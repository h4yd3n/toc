"""§5.10a taskings that create things when accepted: a collection ask opens an operation, a supply ask books a shipment,
a comms ask becomes a task on the subject's operation — and finishing the thing completes the tasking."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

def U(uid): return {"X-TOC-User": uid}
BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


def test_a_collection_tasking_opens_an_operation_and_the_operation_closes_it(client):
    r = client.post("/v1/cop/taskings", json={"kind": "collection", "title": "Overwatch of the FARP at dusk", "from_section": "S2", "to_section": "S3", "subject_type": "location", "subject_id": "loc_farp",
                                            "subject_name": "FARP Eagle", "asset": "One AH-64 pair, 1 h", "priority": "priority", "window_from": "2026-09-20T01:00:00Z", "window_to": "2026-09-20T02:00:00Z"}, headers=U("u_analyst"))
    tid = r.json()["id"]
    r = client.patch(f"/v1/cop/taskings/{tid}", json={"status": "accepted"}, headers=U("u_ea"))
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["created_type"] == "operation" and t["created_id"].startswith("op_") and t["created_name"].startswith("COLLECTION — Overwatch")
    op = client.get(f"/v1/cop/operations/{t['created_id']}").json()
    assert op["subject_id"] == "loc_farp" and op["from_product_type"] == "tasking" and op["from_product_id"] == tid and op["tasks_total"] == 4
    assert {x["section"] for x in op["tasks"]} == {"S2", "S3"} and op["notes"].startswith("One AH-64 pair")
    # accepting twice does not open twice
    assert client.patch(f"/v1/cop/taskings/{tid}", json={"status": "scheduled"}, headers=U("u_ea")).json()["created_id"] == t["created_id"]
    # the ledger tells the story on both objects
    log = client.get("/v1/cop/log?limit=6").json()
    assert any(e["type"] == "cop.operation.opened" and f"from tasking {tid}" in e["summary"] for e in log)
    # closing the operation completes the tasking
    r = client.patch(f"/v1/cop/operations/{op['id']}", json={"status": "complete"}, headers=BC)
    assert r.status_code == 200
    t = next(x for x in client.get("/v1/cop/snapshot").json()["taskings"]["items"] if x["id"] == tid)
    assert t["status"] == "complete" and t["result"].startswith("Operation complete") and not t["open"]


def test_completing_the_tasking_closes_what_it_made(client):
    r = client.post("/v1/cop/taskings", json={"kind": "collection", "title": "Route recon, MSR north", "from_section": "S2", "to_section": "S3", "subject_type": "event", "subject_id": "evt_gunnery", "subject_name": "Aerial Gunnery"}, headers=U("u_analyst"))
    tid = r.json()["id"]
    op_id = client.patch(f"/v1/cop/taskings/{tid}", json={"status": "accepted"}, headers=U("u_ea")).json()["created_id"]
    r = client.patch(f"/v1/cop/taskings/{tid}", json={"status": "complete", "result": "Flown; route clear"}, headers=U("u_ea"))
    assert r.json()["status"] == "complete"
    assert client.get(f"/v1/cop/operations/{op_id}").json()["status"] == "complete"


def test_a_supply_tasking_becomes_a_shipment_and_arrival_completes_it(client):
    r = client.post("/v1/cop/taskings", json={"kind": "supply", "title": "Water at FOB Warrior", "from_section": "S3", "to_section": "S4", "subject_type": "location", "subject_id": "loc_fob", "subject_name": "FOB Warrior — JRTC",
                                            "asset": "600 cases bottled water", "priority": "urgent", "window_from": "2026-09-21T06:00:00Z"}, headers=U("u_ea"))
    tid = r.json()["id"]
    t = client.patch(f"/v1/cop/taskings/{tid}", json={"status": "accepted"}, headers=U("u_logistics")).json()
    assert t["created_type"] == "shipment" and t["created_id"].startswith("shp_")
    snap = client.get("/v1/cop/snapshot").json()
    sh = next(x for x in snap["s4"]["shipments"] if x["id"] == t["created_id"])
    assert sh["category"] == "water" and sh["to_location_id"] == "loc_fob" and sh["status"] == "planned" and sh["priority"] == "urgent" and sh["eta"].startswith("2026-09-21T06:00") and sh["ref"] == tid
    assert client.patch(f"/v1/cop/shipments/{sh['id']}", json={"status": "in_transit"}, headers=U("u_logistics")).status_code == 200
    assert next(x for x in client.get("/v1/cop/snapshot").json()["taskings"]["items"] if x["id"] == tid)["status"] == "accepted"
    client.patch(f"/v1/cop/shipments/{sh['id']}", json={"status": "arrived"}, headers=U("u_logistics"))
    t = next(x for x in client.get("/v1/cop/snapshot").json()["taskings"]["items"] if x["id"] == tid)
    assert t["status"] == "complete" and t["result"].startswith("Arrived")
    # a fuel ask is categorised as fuel
    r = client.post("/v1/cop/taskings", json={"kind": "supply", "title": "JP-8 at the FARP", "from_section": "S3", "to_section": "S4", "subject_type": "location", "subject_id": "loc_farp", "asset": "JP-8 5,000 gal"}, headers=U("u_ea"))
    t2 = client.patch(f"/v1/cop/taskings/{r.json()['id']}", json={"status": "accepted"}, headers=U("u_logistics")).json()
    assert next(x for x in client.get("/v1/cop/snapshot").json()["s4"]["shipments"] if x["id"] == t2["created_id"])["category"] == "fuel"


def test_a_comms_tasking_becomes_a_task_on_the_subjects_operation(client):
    # no operation on the event yet → nothing is created; the tasking still works as a plain ask
    r = client.post("/v1/cop/taskings", json={"kind": "comms", "title": "Confirm PACE for the gunnery", "from_section": "S3", "to_section": "S6", "subject_type": "event", "subject_id": "evt_change", "subject_name": "Change of Command"}, headers=U("u_ea"))
    t = client.patch(f"/v1/cop/taskings/{r.json()['id']}", json={"status": "accepted"}, headers=U("u_signal")).json()
    assert t["created_type"] is None
    # with an operation on the event, the ask becomes a task owned by S6, and finishing the task completes the tasking
    op = client.post("/v1/cop/operations", json={"subject_type": "event", "subject_id": "evt_change"}, headers=BC).json()
    r = client.post("/v1/cop/taskings", json={"kind": "comms", "title": "Retrans for the ceremony net", "from_section": "S3", "to_section": "S6", "subject_type": "event", "subject_id": "evt_change", "subject_name": "Change of Command", "asset": "One retrans team"}, headers=U("u_ea"))
    tid = r.json()["id"]
    t = client.patch(f"/v1/cop/taskings/{tid}", json={"status": "accepted"}, headers=U("u_signal")).json()
    assert t["created_type"] == "task" and t["created_parent"] == op["id"]
    task = next(x for x in client.get(f"/v1/cop/operations/{op['id']}").json()["tasks"] if x["id"] == t["created_id"])
    assert task["section"] == "S6" and task["title"] == "Retrans for the ceremony net" and task["note"] == "One retrans team"
    client.patch(f"/v1/cop/operations/{op['id']}/tasks/{task['id']}", json={"status": "done", "note": "Retrans on the ridge"}, headers=U("u_signal"))
    t = next(x for x in client.get("/v1/cop/snapshot").json()["taskings"]["items"] if x["id"] == tid)
    assert t["status"] == "complete" and "Retrans on the ridge" in t["result"]
