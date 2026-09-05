"""§11.2 the profile: military (S1–S6, the brigade) or corporate (S1–S3, the executive-protection sample), switched from the wall."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None); os.environ.pop("TOC_SECTIONS", None); os.environ.pop("TOC_PROFILE", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_switching_profiles_reshapes_the_sections_and_reloads_the_force(client):
    assert client.put("/v1/cop/profile", json={"profile": "corporate"}, headers={"X-TOC-Role": "ea"}).status_code == 403
    r = client.put("/v1/cop/profile", json={"profile": "military"}, headers=BC)
    assert r.status_code == 200 and r.json()["dataset"] == "cab", r.text
    snap = client.get("/v1/cop/snapshot").json()
    cfg = {s["code"]: s for s in snap["sections"]}
    assert snap["profile"] == "military" and cfg["S4"]["enabled"] and cfg["S6"]["enabled"] and cfg["S1"]["label"] == "S1" and cfg["S1"]["show_code"]
    assert len(snap["people"]) > 2000 and any(t["echelon"] == "brigade" for t in snap["teams"])
    r = client.put("/v1/cop/profile", json={"profile": "corporate"}, headers=BC)
    assert r.status_code == 200 and r.json()["dataset"] == "corporate"
    snap = client.get("/v1/cop/snapshot").json()
    cfg = {s["code"]: s for s in snap["sections"]}
    assert snap["profile"] == "corporate" and not cfg["S4"]["enabled"] and not cfg["S6"]["enabled"]
    assert cfg["S1"]["label"] == "S1" and cfg["S1"]["show_code"] and cfg["S1"]["title"] == "PERSONNEL"  # the same names as before
    assert not any(t["parent_id"] for t in snap["teams"])  # the corporate sample keeps its flat team list
    assert len(snap["people"]) < 200 and any(p["id"] == "p_ceo" for p in snap["people"])
    listing = {s["name"]: s for s in client.get("/v1/cop/settings", headers=BC).json()["settings"]}
    assert listing["TOC_PROFILE"]["value"] == "corporate"
    assert client.put("/v1/cop/profile", json={"profile": "navy"}, headers=BC).status_code == 422
    client.put("/v1/cop/profile", json={"profile": "military"}, headers=BC)
