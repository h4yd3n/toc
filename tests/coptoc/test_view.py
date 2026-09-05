"""§3.1 the opening frame: the wall opens on the declared AO, else on the box that holds our own sites."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app
from coptoc.service import default_view


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


class FakeSite:
    def __init__(self, lat, lon, sensitivity="normal"):
        self.lat, self.lon, self.sensitivity = lat, lon, sensitivity


def test_no_ao_frames_our_own_sites(client, monkeypatch):
    """With no AO declared the frame is the force's own footprint — never a point in the ocean."""
    snap = client.get("/v1/cop/snapshot").json()
    v = snap["view"]
    assert v["source"] == "force"
    sites = [l for l in snap["locations"] if l["sensitivity"] != "restricted"]
    lats = [l["lat"] for l in sites]; lons = [l["lon"] for l in sites]
    assert min(lats) <= v["center_lat"] <= max(lats)
    assert min(lons) <= v["center_lon"] <= max(lons)
    assert v["radius_km"] >= 25.0


def test_declared_ao_wins(monkeypatch):
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: "36.66,-87.48,150" if name == "TOC_AO" else None)
    v = default_view([FakeSite(48.86, 2.35)])
    assert v == {"center_lat": 36.66, "center_lon": -87.48, "radius_km": 150.0, "source": "ao"}


def test_ao_without_a_radius_and_a_junk_ao(monkeypatch):
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: "36.66,-87.48" if name == "TOC_AO" else None)
    assert default_view([])["radius_km"] == 250.0
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: "Fort Campbell" if name == "TOC_AO" else None)
    assert default_view([])["source"] == "none"          # unparseable is not fatal; we just don't know where to look
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: "91,0" if name == "TOC_AO" else None)
    assert default_view([])["source"] == "none"          # off the globe


def test_restricted_sites_never_move_the_board(monkeypatch):
    """Everyone opens on the same board whether or not they are cleared for the residence layer."""
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: None)
    sites = [FakeSite(36.6, -87.4), FakeSite(36.7, -87.5)]
    cleared = default_view(sites + [FakeSite(0.0, 0.0, "restricted")])
    assert cleared == default_view(sites)


def test_a_single_site_is_not_framed_to_street_level(monkeypatch):
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: None)
    v = default_view([FakeSite(38.9, -77.0)])
    assert v["center_lat"] == 38.9 and v["radius_km"] == 25.0


def test_an_empty_wall_admits_it_knows_nothing(monkeypatch):
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: None)
    assert default_view([]) == {"center_lat": None, "center_lon": None, "radius_km": None, "source": "none"}
