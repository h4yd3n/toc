"""§5.6a the rated area assessment: S2 judges a place indicator by indicator; the site, its trips, and its events carry the strip."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app
from coptoc.areas import indicators, normalize

def U(uid): return {"X-TOC-User": uid}
BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


def test_the_brigade_has_three_places_assessed_and_the_sites_carry_the_strip(client):
    snap = client.get("/v1/cop/snapshot").json()
    areas = snap["areas"]
    assert [a["place"] for a in areas][:1] == ["FARP Eagle"]  # the worst-rated place sorts first
    farp = areas[0]
    assert farp["worst"] == "red" and farp["worst_indicator"] == "Sustainment & resupply" and farp["counts"]["red"] == 1
    assert len(farp["ratings"]) == len(indicators("military")) and all(r["note"] for r in farp["ratings"])
    site = next(l for l in snap["locations"] if l["id"] == "loc_farp")
    assert site["area"]["worst"] == "red" and len(site["area"]["strip"]) == 10 and site["area"]["assessed_by"] == "S2 Intelligence"
    # the trips and the event going to a rated place carry it too; a place nobody rated carries nothing
    ev = next(e for e in snap["events"] if e["id"] == "evt_ftx")
    assert ev["area"]["place"] == "FOB Warrior — JRTC"
    assert any(t["area"] and t["area"]["place"] == "FARP Eagle" for t in snap["trips"])
    assert next(l for l in snap["locations"] if l["id"] == "loc_bde")["area"] is None


def test_the_indicator_list_is_configuration(client, monkeypatch):
    assert client.get("/v1/cop/areas/indicators").json()["profile"] == "military"
    monkeypatch.setattr("coptoc.areas.settings.get", lambda name, default=None: "perimeter=Fence line, Crowds, medical=Casualty evacuation" if name == "TOC_AREA_INDICATORS" else None)
    inds = indicators("military")
    assert [i["id"] for i in inds] == ["perimeter", "crowds", "medical"] and inds[1]["label"] == "Crowds"
    rows = normalize([{"indicator": "medical", "rating": "red", "note": "no MEDEVAC"}, {"indicator": "bogus", "rating": "green"}], inds)
    assert [r["rating"] for r in rows] == ["unknown", "unknown", "red"]   # unrated is unknown; unknown indicators are dropped


def test_s2_assesses_a_site_and_supersedes_the_last(client):
    body = {"location_id": "loc_range", "summary": "Reassessed after the recon.", "ratings": [{"indicator": "weather", "rating": "red", "note": "Bird strike on the recon pair"}, {"indicator": "routes", "rating": "green", "note": "Clear"}]}
    assert client.post("/v1/cop/areas", json=body, headers=U("u_signal")).status_code == 403   # S6 does not rate places
    r = client.post("/v1/cop/areas", json=body, headers=U("u_analyst"))
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["place"] == "Peason Ridge Range Complex" and a["worst"] == "red" and a["counts"]["unknown"] == 8 and a["supersedes"] == "area_003"
    assert a["assessed_by"] == "S2 Intelligence" and a["lat"] == 31.4
    current = client.get("/v1/cop/areas").json()
    assert sum(1 for x in current if x["location_id"] == "loc_range") == 1 and next(x for x in current if x["location_id"] == "loc_range")["id"] == a["id"]
    history = client.get("/v1/cop/areas?all=true").json()
    assert next(x for x in history if x["id"] == "area_003")["status"] == "superseded"
    # the site now carries the new judgment; the ledger has the event; the brief buckets it as intel
    site = next(l for l in client.get("/v1/cop/snapshot").json()["locations"] if l["id"] == "loc_range")
    assert site["area"]["id"] == a["id"] and site["area"]["worst"] == "red"
    log = client.get("/v1/cop/log?limit=1").json()[0]
    assert log["type"] == "cop.area.assessed" and "supersedes the last" in log["summary"]
    # amend in place: a note and a rating, no new version
    r = client.patch(f"/v1/cop/areas/{a['id']}", json={"ratings": [{"indicator": "weather", "rating": "amber", "note": "NOTAM only; the pair was not struck"}]}, headers=U("u_analyst"))
    assert r.status_code == 200 and r.json()["worst"] == "amber" and r.json()["id"] == a["id"]
    assert client.patch("/v1/cop/areas/area_003", json={"summary": "x"}, headers=U("u_analyst")).status_code == 409


def test_a_place_that_is_not_a_site(client):
    r = client.post("/v1/cop/areas", json={"place": "Alexandria, LA", "lat": 31.31, "lon": -92.45, "ratings": [{"indicator": "unrest", "rating": "green", "note": "quiet"}]}, headers=BC)
    assert r.status_code == 201 and r.json()["location_id"] is None and r.json()["worst"] == "green"
    assert client.post("/v1/cop/areas", json={"ratings": []}, headers=BC).status_code == 422
