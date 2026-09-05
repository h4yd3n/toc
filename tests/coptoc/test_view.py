"""§3.1 the opening frame: a station that remembers a board opens on it; one that does not asks the server, and the
server answers with the declared AO or home station — the site of type "hq", read from the data."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app
from coptoc.service import HQ_VIEW_RADIUS_KM, REGIONAL_KM, command_post, default_view


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


class FakeSite:
    def __init__(self, lat, lon, type="office", sensitivity="standard", is_toc=False):
        self.lat, self.lon, self.type, self.sensitivity, self.is_toc = lat, lon, type, sensitivity, is_toc


def no_ao(monkeypatch):
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: None)


def test_the_brigade_opens_on_its_own_TOC(client):
    """The military sample is a CAB at Fort Campbell: the board opens on the brigade TOC, not on open water."""
    snap = client.get("/v1/cop/snapshot").json()
    v, hq = snap["view"], next(l for l in snap["locations"] if l["type"] == "hq")
    assert v["source"] == "hq"
    assert (v["center_lat"], v["center_lon"]) == (hq["lat"], hq["lon"])


def test_the_headquarters_is_read_from_the_data(monkeypatch):
    """Move the headquarters and the board moves with it — no coordinates written down in the code."""
    no_ao(monkeypatch)
    texas, baghdad = FakeSite(32.75, -97.33, "hq"), FakeSite(33.31, 44.36, "hq")
    assert default_view([FakeSite(0, 0), texas])["center_lon"] == -97.33
    assert default_view([FakeSite(0, 0), baghdad])["center_lon"] == 44.36
    assert default_view([texas])["radius_km"] == HQ_VIEW_RADIUS_KM


def test_the_board_widens_to_take_in_the_units_around_the_headquarters(monkeypatch):
    """A commander should see the TOC and the subordinate units without touching anything."""
    no_ao(monkeypatch)
    hq = FakeSite(36.67, -87.50, "hq")
    near = FakeSite(37.57, -87.50)                      # ~100 km north — same region
    assert default_view([hq, near])["radius_km"] == pytest.approx(125, rel=0.05)   # the 100 km reach plus its margin
    assert default_view([hq, near])["center_lat"] == 36.67   # still centred on the headquarters


def test_a_unit_on_the_other_side_of_the_country_does_not_pull_the_board_out(monkeypatch):
    """FOB Warrior is 600 km from Campbell: framing both would leave nothing legible on either."""
    no_ao(monkeypatch)
    hq, far = FakeSite(36.67, -87.50, "hq"), FakeSite(31.06, -93.20, "fob")
    assert default_view([hq, far])["radius_km"] == HQ_VIEW_RADIUS_KM
    beyond = FakeSite(36.67 + (REGIONAL_KM + 50) / 111, -87.50)
    assert default_view([hq, beyond])["radius_km"] == HQ_VIEW_RADIUS_KM


def test_no_hq_falls_back_to_a_site_we_do_have(monkeypatch):
    no_ao(monkeypatch)
    assert default_view([FakeSite(48.86, 2.35, "office")])["center_lat"] == 48.86


def test_a_restricted_site_never_sets_the_board(monkeypatch):
    """Every station opens on the same board, cleared for the residence layer or not."""
    no_ao(monkeypatch)
    residence = FakeSite(0.0, 0.0, "residence", "restricted")
    assert command_post([residence, FakeSite(36.67, -87.5, "hq")]).lat == 36.67
    assert default_view([residence])["source"] == "none"


def test_the_board_follows_the_TOC_when_it_jumps(monkeypatch):
    """Garrisoned at Fort Worth, deployed to Baghdad: home station stays in the list, the board goes with the TOC."""
    no_ao(monkeypatch)
    fort_worth = FakeSite(32.75, -97.33, "hq")
    baghdad = FakeSite(33.31, 44.36, "cp", is_toc=True)
    assert default_view([fort_worth])["center_lon"] == -97.33
    assert default_view([fort_worth, baghdad])["center_lon"] == 44.36
    assert command_post([fort_worth, baghdad]) is baghdad


def test_declared_ao_wins_over_the_headquarters(monkeypatch):
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: "33.31,44.36,60" if name == "TOC_AO" else None)
    assert default_view([FakeSite(36.67, -87.5, "hq")]) == {"center_lat": 33.31, "center_lon": 44.36, "radius_km": 60.0, "source": "ao"}


def test_an_ao_without_a_radius_gets_one(monkeypatch):
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: "36.66,-87.48" if name == "TOC_AO" else None)
    assert default_view([])["radius_km"] == 250.0


def test_a_junk_ao_falls_through_rather_than_failing(monkeypatch):
    """Unparseable or off the globe is not fatal — we fall back to the headquarters."""
    for junk in ("Fort Campbell", "91,0", "36.66", "0,0,-5"):
        monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None, j=junk: j if name == "TOC_AO" else None)
        assert default_view([FakeSite(36.67, -87.5, "hq")])["source"] == "hq", junk
