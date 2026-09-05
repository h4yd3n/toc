"""§3.4 the graphics object: a control measure a section draws by hand — typed from a catalog, owned by a section, on the ledger, retired not deleted."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app
from coptoc.graphics import CATALOG, validate

def U(uid): return {"X-TOC-User": uid}
BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


def test_the_brigade_has_its_control_measures_on_the_board(client):
    snap = client.get("/v1/cop/snapshot").json()
    g = snap["graphics"]
    assert len(g) == 9 and {x["section"] for x in g} == {"S2", "S3", "S4", "S6"}
    msr = next(x for x in g if x["type"] == "msr")
    assert msr["kind"] == "line" and msr["label"].startswith("MSR") and msr["color"] and len(msr["geometry"]) == 5 and msr["subject_id"] == "evt_ftx"
    rng = next(x for x in g if x["type"] == "range")
    assert rng["kind"] == "polygon" and rng["in_window"] is False and rng["window_from"]   # hot only during the gunnery
    assert all(len(x["center"]) == 2 for x in g)
    cat = client.get("/v1/cop/graphics/catalog").json()
    assert cat["profile"] == "military" and any(t["type"] == "acp" and t["label"].startswith("ACP") for t in cat["types"])


def test_validation_speaks_plainly():
    assert validate("msr", "point", [1, 2]).startswith("a msr is drawn as line")
    assert validate("acp", "point", [200, 2]) == "each point is [lon, lat]"
    assert validate("cordon", "polygon", [[0, 0], [1, 1]]) == "a polygon needs three points"
    assert validate("msr", "line", [[0, 0], [1, 1]]) == ""
    assert all(c["section"] in ("S2", "S3", "S4", "S6") for c in CATALOG.values())


def test_a_section_draws_its_own_and_retires_it(client):
    body = {"type": "checkpoint", "kind": "point", "name": "CP 7 — bridge north of the FARP", "geometry": [-93.31, 31.2], "note": "Weight-posted bridge.", "subject_type": "event", "subject_id": "evt_ftx"}
    assert client.post("/v1/cop/graphics", json=body, headers=U("u_signal")).status_code == 403   # S6 does not draw S3's checkpoints
    r = client.post("/v1/cop/graphics", json=body, headers=U("u_ea"))
    assert r.status_code == 201, r.text
    g = r.json(); gid = g["id"]
    assert g["section"] == "S3" and g["status"] == "active" and g["created_by"] == "S3 Operations" and g["glyph"]
    assert client.post("/v1/cop/graphics", json={**body, "kind": "line"}, headers=U("u_ea")).status_code == 422
    assert client.post("/v1/cop/graphics", json={**body, "name": " "}, headers=U("u_ea")).status_code == 422
    log = client.get("/v1/cop/log?limit=1").json()[0]
    assert log["type"] == "cop.graphic.drawn" and "CP 7" in log["summary"]
    # move it, then retire it: gone from the board, kept in the record
    r = client.patch(f"/v1/cop/graphics/{gid}", json={"geometry": [-93.30, 31.21], "note": "Moved to the near bank."}, headers=U("u_ea"))
    assert r.status_code == 200 and r.json()["geometry"] == [-93.30, 31.21]
    assert client.patch(f"/v1/cop/graphics/{gid}", json={"status": "retired"}, headers=BC).json()["status"] == "retired"
    assert not any(x["id"] == gid for x in client.get("/v1/cop/snapshot").json()["graphics"])
    assert any(x["id"] == gid and x["status"] == "retired" for x in client.get("/v1/cop/graphics?all=true").json())
    assert client.get("/v1/cop/log?limit=1").json()[0]["type"] == "cop.graphic.retired"


def test_an_s2_tai_and_an_s6_retrans_belong_to_their_sections(client):
    r = client.post("/v1/cop/graphics", json={"type": "tai", "kind": "polygon", "name": "TAI 2", "geometry": [[-93.3, 31.1], [-93.2, 31.1], [-93.2, 31.2]]}, headers=U("u_analyst"))
    assert r.status_code == 201 and r.json()["section"] == "S2" and r.json()["dash"] is True
    r = client.post("/v1/cop/graphics", json={"type": "retrans", "kind": "point", "name": "RRT 2", "geometry": [-93.3, 31.3]}, headers=U("u_signal"))
    assert r.status_code == 201 and r.json()["section"] == "S6"
    assert client.post("/v1/cop/graphics", json={"type": "retrans", "kind": "point", "name": "RRT 3", "geometry": [-93.3, 31.3]}, headers=U("u_analyst")).status_code == 403
