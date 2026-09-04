"""§6: the long-range planning view and security coverage per event."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}
EA = {"X-TOC-Role": "ea", "X-TOC-Actor": "ea"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        yield c


def test_planning_view_groups_by_week_and_shows_coverage_gaps(client):
    p = client.get("/v1/cop/planning", params={"days": 90}).json()
    assert p["summary"]["events"] == 3 and p["summary"]["trips"] >= 5 and p["summary"]["security_available"] >= 10
    assert all(w["week"] <= w2["week"] for w, w2 in zip(p["weeks"], p["weeks"][1:]))
    board = next(e for w in p["weeks"] for e in w["events"] if e["id"] == "evt_001")
    assert board["coverage"]["required"] == 1 + board["vip_count"] and board["coverage"]["assigned"] == 0 and board["coverage"]["gap"] == board["coverage"]["required"]
    assert any(g["event_id"] == "evt_001" for g in p["gaps"])


def test_assign_coverage_is_gated_security_only_and_logged(client):
    p = client.get("/v1/cop/planning").json()
    sec = [s for s in p["security"] if s["home_location_id"] == "loc_nyc"]
    assert sec, "seed has NYC security"
    assert client.post("/v1/cop/events/evt_001/coverage", json={"person_id": sec[0]["id"], "role": "lead"}, headers=EA).status_code == 403
    assert client.post("/v1/cop/events/evt_001/coverage", json={"person_id": "p_ceo", "role": "lead"}, headers=BC).status_code == 422  # not security
    r = client.post("/v1/cop/events/evt_001/coverage", json={"person_id": sec[0]["id"], "role": "lead"}, headers=BC)
    assert r.status_code == 201 and r.json()["overlaps"] == []
    assert client.post("/v1/cop/events/evt_001/coverage", json={"person_id": sec[0]["id"], "role": "agent"}, headers=BC).status_code == 409
    ev = client.get("/v1/cop/events/evt_001").json() if client.get("/v1/cop/events/evt_001").status_code == 200 else None
    snap = client.get("/v1/cop/snapshot").json()
    e = next(x for x in snap["events"] if x["id"] == "evt_001")
    assert e["coverage"]["assigned"] == 1 and e["coverage"]["people"][0]["role"] == "lead" and e["coverage"]["gap"] == e["coverage"]["required"] - 1
    # the Battle Captain can override the rule
    client.patch("/v1/cop/events/evt_001", json={"required_security": 1}, headers=BC)
    e = next(x for x in client.get("/v1/cop/snapshot").json()["events"] if x["id"] == "evt_001")
    assert e["coverage"]["required"] == 1 and e["coverage"]["gap"] == 0 and e["coverage"]["rule"] == "override"
    p = client.get("/v1/cop/planning").json()
    who = next(s for s in p["security"] if s["id"] == sec[0]["id"])
    assert who["commitments"] and who["commitments"][0]["event_id"] == "evt_001"
    assert client.delete(f"/v1/cop/events/evt_001/coverage/{sec[0]['id']}", headers=BC).json()["status"] == "removed"
    types = [x["type"] for x in client.get("/v1/cop/log", params={"limit": 6}).json()]
    assert "cop.event.coverage" in types
