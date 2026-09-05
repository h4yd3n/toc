"""§5.10 taskings: one section raises, another accepts, schedules, completes, or declines; the brief carries what is open."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

def U(uid): return {"X-TOC-User": uid}
BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed?dataset=cab")
        yield c


def test_seeded_taskings_and_roll_up(client):
    snap = client.get("/v1/cop/snapshot").json()
    tk = snap["taskings"]
    assert tk["open"] == 5 and tk["overdue"] == 1  # SIPR at the FOB is inside its window and still scheduled
    per = tk["per_section"]
    assert per["S6"]["inbox"] == 2 and per["S3"]["outbox"] == 4 and per["S3"]["inbox"] == 1 and per["S6"]["overdue"] == 1
    assert snap["summary"]["taskings_open"] == 5
    first = tk["items"][0]
    assert first["open"] and first["health"] == "red"  # the overdue one sorts first
    done = next(x for x in tk["items"] if x["status"] == "complete")
    assert done["result"].startswith("Flown")


def test_raise_accept_complete_and_decline(client):
    # S2 raises a collection tasking on S3
    r = client.post("/v1/cop/taskings", json={"kind": "collection", "title": "Overwatch of MSR at dusk", "from_section": "S2", "to_section": "S3", "subject_type": "location", "subject_id": "loc_range",
                                            "subject_name": "Peason Ridge Range Complex", "asset": "One AH-64 pair, 1 h", "priority": "priority", "window_from": "2026-09-20T01:00:00Z", "window_to": "2026-09-20T02:00:00Z"}, headers=U("u_analyst"))
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    assert r.json()["status"] == "requested" and r.json()["requested_by"] == "S2 Intelligence"
    # the wrong section cannot answer it; the right one can
    assert client.patch(f"/v1/cop/taskings/{tid}", json={"status": "accepted"}, headers=U("u_signal")).status_code == 403
    r = client.patch(f"/v1/cop/taskings/{tid}", json={"status": "accepted"}, headers=U("u_ea"))
    assert r.status_code == 200 and r.json()["owned_by"] == "S3 Operations"
    r = client.patch(f"/v1/cop/taskings/{tid}", json={"status": "scheduled", "notes": "B/1 pair, 0100Z"}, headers=U("u_ea"))
    assert r.json()["status"] == "scheduled" and r.json()["notes"] == "B/1 pair, 0100Z"
    r = client.patch(f"/v1/cop/taskings/{tid}", json={"status": "complete", "result": "Flown; nothing significant to report"}, headers=U("u_ea"))
    assert r.json()["status"] == "complete" and not r.json()["open"]
    assert client.patch(f"/v1/cop/taskings/{tid}", json={"status": "accepted"}, headers=U("u_ea")).status_code == 409
    log = client.get("/v1/cop/log?limit=1").json()[0]
    assert log["type"] == "cop.tasking.complete" and "S2 → S3" in log["summary"]
    # declining needs a reason
    r = client.post("/v1/cop/taskings", json={"title": "Fuel at the range", "from_section": "S3", "to_section": "S4", "kind": "supply", "asset": "JP-8 2,000 gal"}, headers=U("u_ea"))
    tid2 = r.json()["id"]
    assert client.patch(f"/v1/cop/taskings/{tid2}", json={"status": "declined"}, headers=U("u_logistics")).status_code == 422
    assert client.patch(f"/v1/cop/taskings/{tid2}", json={"status": "declined", "result": "No tanker available before D-1"}, headers=U("u_logistics")).status_code == 200
    # the raiser may amend a requested ask; a section cannot task itself; a tasking must go somewhere else
    r = client.post("/v1/cop/taskings", json={"title": "x", "from_section": "S3", "to_section": "S3"}, headers=U("u_ea"))
    assert r.status_code == 422
    assert client.post("/v1/cop/taskings", json={"title": "y", "from_section": "S2", "to_section": "S3"}, headers=U("u_logistics")).status_code == 403


def test_brief_carries_open_taskings(client):
    client.post("/v1/cop/watch/take", json={"battle_captain": "bc"}, headers=BC)
    brief = client.get("/v1/cop/watch/brief").json()
    open_ = brief["current_status"]["taskings"]
    assert open_ and all(x["status"] in ("requested", "accepted", "scheduled") for x in open_) and any(x["overdue"] for x in open_)
