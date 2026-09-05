"""§3.1 the opening frame: a station that remembers a board opens on it; one that does not asks the server, and the
server answers with the declared AO or this deployment's home ground."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app
from coptoc.service import HOME_GROUND, default_view


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


def no_ao(monkeypatch):
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: None)


def test_the_snapshot_carries_a_frame(client):
    v = client.get("/v1/cop/snapshot").json()["view"]
    assert v["source"] in {"ao", "profile"}
    assert v["center_lat"] is not None and v["center_lon"] is not None and v["radius_km"] > 0


def test_home_ground_follows_the_profile(monkeypatch):
    """A unit opens on Baghdad, a company on the Bay Area — opinions about who is running this, overridable by TOC_AO."""
    no_ao(monkeypatch)
    monkeypatch.setattr("coptoc.service.toc_profile", lambda: "military")
    assert default_view() == {**HOME_GROUND["military"], "source": "profile"}
    monkeypatch.setattr("coptoc.service.toc_profile", lambda: "corporate")
    assert default_view() == {**HOME_GROUND["corporate"], "source": "profile"}


def test_an_unknown_profile_still_gets_a_board(monkeypatch):
    no_ao(monkeypatch)
    monkeypatch.setattr("coptoc.service.toc_profile", lambda: "something-else")
    assert default_view()["source"] == "profile" and default_view()["center_lat"] is not None


def test_declared_ao_wins(monkeypatch):
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: "36.66,-87.48,150" if name == "TOC_AO" else None)
    assert default_view() == {"center_lat": 36.66, "center_lon": -87.48, "radius_km": 150.0, "source": "ao"}


def test_an_ao_without_a_radius_gets_one(monkeypatch):
    monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None: "36.66,-87.48" if name == "TOC_AO" else None)
    assert default_view()["radius_km"] == 250.0


def test_a_junk_ao_falls_through_rather_than_failing(monkeypatch):
    """Unparseable or off the globe is not fatal — we just fall back to home ground."""
    for junk in ("Fort Campbell", "91,0", "36.66", "0,0,-5"):
        monkeypatch.setattr("coptoc.service.settings.get", lambda name, default=None, j=junk: j if name == "TOC_AO" else None)
        assert default_view()["source"] == "profile", junk
