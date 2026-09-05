"""§9 users and permissions: sign in as a user, see and change only what your permissions allow; the admin grants them."""
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


def test_signing_in_resolves_role_and_perms(client):
    me = client.get("/v1/cop/me", headers=U("u_logistics")).json()
    assert me["name"] == "S4 Logistics" and me["role"] == "logistics" and me["perms"] == {"S1": "view", "S3": "view", "S4": "edit"}
    assert me["sections_visible"] == ["S1", "S3", "S4"] and not me["battle_captain"] and not me["admin"]
    bc = client.get("/v1/cop/me", headers=U("u_battle_captain")).json()
    assert bc["role"] == "battle_captain" and bc["sections_visible"] == ["S1", "S2", "S3", "S4", "S6"] and bc["admin"]
    anon = client.get("/v1/cop/me", headers={"X-TOC-Role": "analyst"}).json()
    assert anon["user_id"] is None and anon["role"] == "analyst"  # the old header path still works
    assert client.get("/v1/cop/snapshot", headers=U("u_analyst")).json()["me"]["role"] == "analyst"


def test_permissions_gate_writes(client):
    # the supply sergeant edits S4 and nothing else
    assert client.patch("/v1/cop/supply/sup_001", json={"on_hand": 1}, headers=U("u_logistics")).status_code == 200
    assert client.patch("/v1/cop/systems/sys_001", json={"status": "down"}, headers=U("u_logistics")).status_code == 403
    assert client.post("/v1/cop/incidents", json={"location_id": "loc_bde"}, headers=U("u_logistics")).status_code == 403
    assert client.get("/v1/cop/settings", headers=U("u_logistics")).status_code == 403
    # a brigade S3 with only S4 view cannot change S4; the Battle Captain can do anything
    assert client.patch("/v1/cop/supply/sup_001", json={"on_hand": 2}, headers=U("u_ea")).status_code == 403
    assert client.patch("/v1/cop/systems/sys_001", json={"status": "up"}, headers=U("u_battle_captain")).status_code == 200
    log = client.get("/v1/cop/log?limit=1").json()[0]
    assert log["actor"] == "Battle Captain"  # the signed-in name is the actor on the ledger


def test_admin_grants_permissions(client):
    assert client.post("/v1/cop/users", json={"name": "x"}, headers=U("u_logistics")).status_code == 403
    r = client.post("/v1/cop/users", json={"name": "SGT Avery Ruiz", "title": "Supply, B/1", "preset": "logistics", "team_id": "t_1atk_b"}, headers=U("u_admin"))
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    assert r.json()["perms"]["S4"] == "edit" and not r.json()["admin"]
    assert client.patch("/v1/cop/systems/sys_001", json={"status": "degraded"}, headers=U(uid)).status_code == 403
    r = client.patch(f"/v1/cop/users/{uid}", json={"perms": {"S6": "edit", "S1": None}}, headers=U("u_admin"))
    assert r.status_code == 200 and r.json()["perms"] == {"S3": "view", "S4": "edit", "S6": "edit"}
    assert client.patch("/v1/cop/systems/sys_001", json={"status": "degraded"}, headers=U(uid)).status_code == 200
    r = client.patch(f"/v1/cop/users/{uid}", json={"battle_captain": True}, headers=U("u_admin"))
    assert client.get("/v1/cop/me", headers=U(uid)).json()["role"] == "battle_captain"
    assert client.patch(f"/v1/cop/users/{uid}", json={"active": False}, headers=U("u_admin")).status_code == 200
    assert client.get("/v1/cop/me", headers=U(uid)).json()["user_id"] is None  # deactivated: back to nobody
    listing = client.get("/v1/cop/users", headers=U("u_logistics")).json()
    assert "perms" not in listing["users"][0] and listing["presets"]["logistics"]["perms"]["S4"] == "edit"
    assert "perms" in client.get("/v1/cop/users", headers=U("u_admin")).json()["users"][0]
    assert client.delete(f"/v1/cop/users/{uid}", headers=U("u_admin")).status_code == 200
    assert client.post("/v1/cop/users", json={"name": "y", "preset": "nope"}, headers=U("u_admin")).status_code == 422


def test_directory_follows_the_dataset(client):
    names = {u["id"] for u in client.get("/v1/cop/users", headers=BC).json()["users"]}
    assert {"u_battle_captain", "u_logistics", "u_signal"} <= names
    client.post("/v1/cop/seed?dataset=corporate")
    names = {u["id"] for u in client.get("/v1/cop/users", headers=BC).json()["users"]}
    assert "u_ep" in names and "u_logistics" not in names
    client.post("/v1/cop/seed?dataset=cab")
