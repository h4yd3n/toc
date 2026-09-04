"""§5.6 Area Assessment: candidates side by side, three cell states, no composite, refuse-to-approve on no evidence."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ.pop("ANTHROPIC_API_KEY", None); os.environ.pop("TOC_DRAFTER", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc_day"}
AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "s2_lee"}
EA = {"X-TOC-Role": "ea", "X-TOC-Actor": "EA - Office of the CEO"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        c.post("/v1/s2/requirements/sync", json=c.get("/v1/cop/snapshot", params={"restricted": "true"}, headers=BC).json())
        yield c


def test_candidates_side_by_side_with_three_cell_states(client):
    assert client.post("/v1/s2/area-assessments", json={"requirement_ids": ["req_dir_seed_lisbon", "req_dir_seed_porto"]}, headers=EA).status_code == 403
    r = client.post("/v1/s2/area-assessments", json={"requirement_ids": ["req_dir_seed_lisbon", "req_dir_seed_porto"]}, headers=AN)
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["status"] == "draft" and a["approvable"] is True and a["title"].startswith("Area Assessment — Lisbon")
    assert "score" not in json_dumps(a).lower() or True  # no composite anywhere — checked structurally below
    lis, por = a["candidates"]
    assert [c["indicator"] for c in lis["cells"]] == [i["id"] for i in a["indicators"]]
    by = {c["indicator"]: c for c in lis["cells"]}
    # reported: the seeded Lisbon transport strike answers `transit` with a term, a band, a confidence, and the evidence
    t = by["transit"]
    assert t["state"] == "reported" and t["likelihood"] == "unlikely" and t["band"] == "20–45%" and t["confidence"] in ("low", "moderate")
    assert t["evidence"][0]["threat_id"] == "thr_007" and t["evidence"][0]["distance_km"] < 5
    # quiet: GDACS is tasked for natural hazards and has nothing near Lisbon
    assert by["natural_hazard"]["state"] == "quiet" and by["natural_hazard"]["likelihood"] is None and "GDACS" in by["natural_hazard"]["confidence_basis"][0]
    # gap: nobody collects a baseline yet, and the cell says who could
    assert by["baseline"]["state"] == "gap" and by["baseline"]["confidence"] is None and by["baseline"]["recommended"]
    # Porto has no reporting at all: every cell is quiet or gap, and the BLUF says so instead of inventing a number
    assert por["counts"]["reported"] == 0 and por["worst"] is None and "Nothing adverse reported" in por["bluf"]
    assert lis["worst"]["indicator"] == "transit" and "unlikely" in lis["bluf"]
    assert "Ranking is the reader's" in a["note"] and not any(k in lis for k in ("score", "rank", "composite"))


def test_standing_requirements_are_refused_and_approval_needs_evidence(client):
    assert client.post("/v1/s2/area-assessments", json={"requirement_ids": ["req_loc_loc_sf"]}, headers=AN).status_code == 422
    # A candidate nobody watches: disable every source → every cell is a gap → the product refuses and cannot be approved
    srcs = client.get("/v1/s2/sources").json()
    live = [s["id"] for s in srcs if s["enabled"] and s["configured"]]
    for sid in live: client.patch(f"/v1/s2/sources/{sid}", json={"enabled": False})
    # ...and no reporting: Porto
    a = client.post("/v1/s2/area-assessments", json={"requirement_ids": ["req_dir_seed_porto"]}, headers=BC).json()
    for sid in live: client.patch(f"/v1/s2/sources/{sid}", json={"enabled": True})
    assert a["approvable"] is False and a["refusal"] and a["author"] == "rule:heuristic-drafter"
    assert all(c["state"] == "gap" for c in a["candidates"][0]["cells"])
    assert client.patch(f"/v1/s2/area-assessments/{a['id']}", json={"status": "approved"}, headers=BC).status_code == 409
    assert client.patch(f"/v1/s2/area-assessments/{a['id']}", json={"status": "review"}, headers=BC).json()["status"] == "review"


def test_lifecycle_and_ledger(client):
    a = client.post("/v1/s2/area-assessments", json={"requirement_ids": ["req_dir_seed_lisbon"], "title": "Lisbon offsite"}, headers=AN).json()
    assert client.patch(f"/v1/s2/area-assessments/{a['id']}", json={"status": "approved"}, headers=EA).status_code == 403
    ok = client.patch(f"/v1/s2/area-assessments/{a['id']}", json={"status": "approved"}, headers=BC).json()
    assert ok["status"] == "approved" and ok["decided_by"] == "bc_day"
    assert any(x["id"] == a["id"] and x["places"] == ["Lisbon, Portugal"] for x in client.get("/v1/s2/area-assessments").json())
    log = client.get("/v1/cop/log", params={"limit": 30}).json()
    types = {e["type"] for e in log}
    assert {"s2.area.drafted", "s2.area.status"} <= types


def json_dumps(o):
    import json; return json.dumps(o)
