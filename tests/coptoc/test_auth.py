"""The sign-in layer in front of the profile picker (README, "Before you deploy").

The prototype's default is unchanged: pick a profile, no password. With TOC_AUTH=on the door closes — a bearer token
is the only identity, the dev secret is refused at startup, and a changed password invalidates the tokens issued
before it."""
import importlib
import os

import pytest
from fastapi.testclient import TestClient

from coptoc.app import app
from coptoc import auth

ADMIN = {"X-TOC-User": "u_admin", "X-TOC-Role": "battle_captain", "X-TOC-Actor": "Admin"}
BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "Captain"}
GOOD = "correct horse battery staple"


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        yield c


def test_the_prototype_still_signs_in_by_picking_a_profile(client):
    assert client.get("/v1/auth/status").json() == {"required": False, "token_hours": auth.TOKEN_HOURS, "scheme": "bearer"}
    assert client.get("/v1/cop/snapshot", headers=BC).status_code == 200, "no password, no token: the demo works"


def test_a_password_is_set_by_an_admin_exchanged_for_a_token_and_never_returned(client):
    r = client.post("/v1/auth/password", json={"user_id": "u_analyst", "password": GOOD}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["password_set"] is True
    # the hash never leaves the server
    listed = next(u for u in client.get("/v1/cop/users", headers=ADMIN).json()["users"] if u["id"] == "u_analyst")
    assert "password_hash" not in listed and listed["has_password"] is True
    assert client.post("/v1/auth/login", json={"user_id": "u_analyst", "password": "wrong"}).status_code == 401
    assert client.post("/v1/auth/login", json={"user_id": "u_nobody", "password": GOOD}).status_code == 401
    ok = client.post("/v1/auth/login", json={"user_id": "u_analyst", "password": GOOD})
    assert ok.status_code == 200, ok.text
    token = ok.json()["token"]
    assert ok.json()["me"]["preset"] == "analyst" and ok.json()["expires_at"]
    # the token resolves the same actor the permission rules already check
    me = client.get("/v1/cop/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["user_id"] == "u_analyst" and me["role"] == "analyst"
    # a forged or edited token is not an identity
    body, sig = token.split(".")
    assert auth.user_for_token(body + "." + sig[:-2] + "xx") is None
    assert auth.read_token("not-a-token") is None


def test_changing_a_password_invalidates_the_tokens_issued_before_it(client):
    client.post("/v1/auth/password", json={"user_id": "u_ea", "password": GOOD}, headers=ADMIN)
    token = client.post("/v1/auth/login", json={"user_id": "u_ea", "password": GOOD}).json()["token"]
    assert auth.user_for_token(token)["id"] == "u_ea"
    # the holder changes it themselves, which needs the current one
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/v1/auth/password", json={"user_id": "u_ea", "password": "another long passphrase"}, headers=headers).status_code == 403
    changed = client.post("/v1/auth/password", json={"user_id": "u_ea", "password": "another long passphrase", "current_password": GOOD}, headers=headers)
    assert changed.status_code == 200 and changed.json()["sessions_invalidated"] is True
    assert auth.user_for_token(token) is None, "the old token stops working the moment the password changes"
    assert auth.user_for_token(client.post("/v1/auth/login", json={"user_id": "u_ea", "password": "another long passphrase"}).json()["token"])["id"] == "u_ea"
    # one profile cannot set another's password
    assert client.post("/v1/auth/password", json={"user_id": "u_analyst", "password": GOOD},
                       headers={"Authorization": f"Bearer {client.post('/v1/auth/login', json={'user_id': 'u_ea', 'password': 'another long passphrase'}).json()['token']}"}).status_code == 403


def test_with_the_door_closed_a_profile_header_is_not_an_identity(client, monkeypatch):
    client.post("/v1/auth/password", json={"user_id": "u_battle_captain", "password": GOOD}, headers=ADMIN)
    token = client.post("/v1/auth/login", json={"user_id": "u_battle_captain", "password": GOOD}).json()["token"]
    monkeypatch.setenv("TOC_AUTH", "on")
    assert client.get("/v1/cop/snapshot", headers=BC).status_code == 401
    assert client.get("/v1/cop/snapshot", headers={"X-TOC-User": "u_battle_captain"}).status_code == 401
    assert client.get("/v1/cop/snapshot", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    # the door is open exactly where it has to be
    assert client.get("/v1/health").status_code == 200
    assert client.get("/v1/auth/status").json()["required"] is True
    assert client.post("/v1/auth/login", json={"user_id": "u_battle_captain", "password": GOOD}).status_code == 200


def test_a_closed_deployment_refuses_the_dev_secret_and_an_open_cors_policy(monkeypatch):
    monkeypatch.setenv("TOC_AUTH", "on")
    monkeypatch.delenv("TOC_SECRET", raising=False)
    monkeypatch.delenv("TOC_ALLOWED_ORIGINS", raising=False)
    with pytest.raises(RuntimeError, match="TOC_SECRET"):
        auth.startup_guard()
    monkeypatch.setenv("TOC_SECRET", "a real secret for this deployment")
    with pytest.raises(RuntimeError, match="TOC_ALLOWED_ORIGINS"):
        auth.startup_guard()
    monkeypatch.setenv("TOC_ALLOWED_ORIGINS", "https://toc.example.mil")
    auth.startup_guard()
    assert auth.allowed_origins() == ["https://toc.example.mil"]


def test_passwords_are_hashed_with_a_salt_and_verified_in_constant_time():
    a, b = auth.hash_password(GOOD), auth.hash_password(GOOD)
    assert a != b and a.startswith("scrypt$") and GOOD not in a
    assert auth.verify_password(GOOD, a) and auth.verify_password(GOOD, b)
    assert not auth.verify_password("wrong", a)
    assert not auth.verify_password(GOOD, None) and not auth.verify_password(GOOD, "plaintext")
