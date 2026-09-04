"""§5.10 #3: a product hands off to an operation — target package → OPORD."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc_day"}
EP = {"X-TOC-Role": "ep", "X-TOC-Actor": "ep_lead"}
S4 = {"X-TOC-Role": "security", "X-TOC-Actor": "S4 logistics"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        yield c


def test_only_an_approved_product_becomes_an_operation(client):
    assert client.post("/v1/cop/operations", json={"subject_type": "location", "subject_id": "loc_dc2", "from_assessment_id": "ASMT-015"}, headers=EP).status_code == 403
    r = client.post("/v1/cop/operations", json={"subject_type": "location", "subject_id": "loc_dc2", "from_assessment_id": "ASMT-015"}, headers=BC)
    assert r.status_code == 409 and "review" in r.json()["detail"]  # ASMT-015 is in review: not a target package yet
    r = client.post("/v1/cop/operations", json={"subject_type": "event", "subject_id": "evt_002", "from_assessment_id": "ASMT-014"}, headers=BC)
    assert r.status_code == 201, r.text
    op = r.json()
    assert op["status"] == "planned" and op["from_product_id"] == "ASMT-014" and op["tasks_total"] == 6 and op["pct"] == 0
    assert {t["section"] for t in op["tasks"]} == {"S1", "S2", "S3", "S6"} and op["title"].startswith("OP — Global Sales Kickoff")


def test_tasks_and_s4_resources_are_worked_and_logged(client):
    op = next(o for o in client.get("/v1/cop/operations").json() if o["subject_id"] == "evt_002")
    t0 = op["tasks"][0]
    assert client.patch(f"/v1/cop/operations/{op['id']}/tasks/{t0['id']}", json={"status": "doing", "owner": "EP advance team"}, headers=EP).json()["status"] == "doing"
    assert client.patch(f"/v1/cop/operations/{op['id']}/tasks/{t0['id']}", json={"status": "done"}, headers=EP).json()["status"] == "done"
    extra = client.post(f"/v1/cop/operations/{op['id']}/tasks", json={"title": "Book medical standby", "section": "S4", "owner": "S4"}, headers=BC)
    assert extra.status_code == 201
    res = client.post(f"/v1/cop/operations/{op['id']}/resources", json={"item": "Radios", "qty": 8}, headers=EP).json()
    assert res["status"] == "requested"
    assert client.patch(f"/v1/cop/operations/{op['id']}/resources/{res['id']}", json={"status": "issued", "note": "from DC-East cage"}, headers=S4).json()["status"] == "issued"
    d = client.get(f"/v1/cop/operations/{op['id']}").json()
    assert d["tasks_total"] == 7 and d["tasks_done"] == 1 and d["resources_open"] == 0 and d["pct"] == 14
    types = [e["type"] for e in client.get("/v1/cop/log", params={"limit": 10}).json()]
    assert "cop.operation.task" in types and "cop.operation.resource" in types and "cop.operation.opened" in types


def test_operation_status_and_the_wall_shows_it_against_the_subject(client):
    snap = client.get("/v1/cop/snapshot").json()
    ev = next(e for e in snap["events"] if e["id"] == "evt_002")
    assert ev["operation"] and ev["operation"]["tasks_total"] == 7 and ev["operation"]["status"] == "planned"
    riyadh = next(t for t in snap["trips"] if t["id"] == "trip_001")
    assert riyadh["operation"]["id"] == "op_seed_riyadh" and riyadh["operation"]["from_product_id"] == "ASMT-014" and riyadh["operation"]["resources_open"] == 1
    op = ev["operation"]
    assert client.patch(f"/v1/cop/operations/{op['id']}", json={"status": "active"}, headers=EP).status_code == 403
    assert client.patch(f"/v1/cop/operations/{op['id']}", json={"status": "complete", "notes": "Event closed without incident."}, headers=BC).json()["status"] == "complete"
    snap = client.get("/v1/cop/snapshot").json()
    assert next(e for e in snap["events"] if e["id"] == "evt_002")["operation"] is None  # complete operations leave the wall
