"""Phase 1 Sigtoc picture: actors, sightings, and report disposition."""
import os
import tempfile

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///" + os.path.join(tempfile.mkdtemp(), "picture.db"))
os.environ["TOC_OFFLINE"] = "1"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["TOC_DRAFTER"] = "heuristic"

from fastapi.testclient import TestClient
from sigtoc.api import standalone_app

AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "s2_lee"}
SEC = {"X-TOC-Role": "security", "X-TOC-Actor": "guard_7"}


def client():
    return TestClient(standalone_app())


def test_analyst_owns_actors_and_sightings():
    with client() as c:
        body = {"kind": "group", "name": "Loading dock surveillance pair", "strength": "two people", "lat": 37.7897, "lon": -122.3989, "place": "north gate"}
        assert c.post("/v1/s2/actors", json=body, headers=SEC).status_code == 403
        r = c.post("/v1/s2/actors", json=body, headers=AN)
        assert r.status_code == 201, r.text
        actor = r.json()
        sighting = c.post(f"/v1/s2/actors/{actor['id']}/sightings", json={"lat": 37.79, "lon": -122.40, "what": "Pair photographed loading dock.", "confidence": "confirmed"}, headers=AN)
        assert sighting.status_code == 201, sighting.text
        detail = c.get(f"/v1/s2/actors/{actor['id']}").json()
        assert detail["last_seen_at"] == sighting.json()["at"] and detail["sightings"][0]["confidence"] == "confirmed"


def test_report_disposition_links_to_an_actor_as_a_sighting():
    with client() as c:
        actor = c.post("/v1/s2/actors", json={"kind": "unit", "name": "OPFOR recon element"}, headers=AN).json()
        report = c.post("/v1/s2/reports", json={"text": "Observed two people with optics west of the FARP.", "reported_by": "guard_7", "lat": 31.153, "lon": -93.344, "place": "FARP west treeline"}, headers=SEC)
        assert report.status_code == 201, report.text
        disp = c.post(f"/v1/s2/reports/{report.json()['id']}/dispose", json={"action": "link", "target_type": "actor", "target_id": actor["id"], "confidence": "probable"}, headers=AN)
        assert disp.status_code == 200, disp.text
        body = disp.json()
        assert body["status"] == "linked" and body["disposition_target_type"] == "sighting" and body["created"]["object_type"] == "sighting"
        detail = c.get(f"/v1/s2/actors/{actor['id']}").json()
        assert detail["lat"] == 31.153 and detail["sightings"][0]["source_id"] == report.json()["id"]


def test_dismissal_needs_a_reason_and_corroboration_improves_credibility():
    with client() as c:
        rid = c.post("/v1/s2/reports", json={"text": "Same vehicle seen again near the north gate.", "reported_by": "guard_7"}, headers=SEC).json()["id"]
        assert c.post(f"/v1/s2/reports/{rid}/dispose", json={"action": "dismiss"}, headers=AN).status_code == 422
        r = c.post(f"/v1/s2/reports/{rid}/dispose", json={"action": "corroborate", "note": "matches camera feed"}, headers=AN)
        assert r.status_code == 200 and r.json()["status"] == "corroborated" and r.json()["grade"] == "A1"
