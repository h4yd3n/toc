"""Phase 1 integration: Sigtoc owns the picture; Cop Talk shows the live slice."""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"
os.environ["TOC_INTSUM_CLOCK"] = "off"
os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "s2_lee"}
SEC = {"X-TOC-Role": "security", "X-TOC-Actor": "guard_7"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


def test_cop_snapshot_carries_the_sigtoc_live_picture(client):
    snap = client.get("/v1/cop/snapshot").json()
    assert snap["s2_actors"] and snap["s2_sightings"]
    assert snap["summary"]["s2_actors"] == len(snap["s2_actors"])
    opfor = next(a for a in snap["s2_actors"] if a["id"] == "act_opfor_recon")
    assert opfor["lat"] is not None and opfor["sighting_ids"]
    threat_gfx = [g for g in snap["graphics"] if g["threat_graphic"]]
    assert {"danger_area", "ambush_site", "avenue_approach", "hostile_op"} <= {g["type"] for g in threat_gfx}
    assert all(g["confidence"] in ("confirmed", "probable", "possible", "template") for g in threat_gfx)


def test_s3_movements_are_flagged_when_they_cross_s2_threat_graphics(client):
    snap = client.get("/v1/cop/snapshot").json()
    risks = snap["movement_risks"]
    assert risks and snap["summary"]["movement_risks"] == len(risks)
    assert any("Danger Area 2" in r["graphic_name"] for r in risks)
    assert any(m.get("risk_flags") for m in snap["movements"])
    farp = [m for m in snap["movements"] if "FARP" in m["dest_name"]]
    assert farp and any(m.get("risk_flags") for m in farp)


def test_report_promotion_creates_a_threat_graphic_visible_on_the_cop(client):
    r = client.post("/v1/s2/reports", json={"text": "Observed a roadblock on the service road.", "reported_by": "guard_7", "lat": 31.11, "lon": -93.27, "place": "service road"}, headers=SEC)
    assert r.status_code == 201, r.text
    disp = client.post(f"/v1/s2/reports/{r.json()['id']}/dispose", json={"action": "promote", "graphic_type": "hostile_checkpoint", "name": "Roadblock - service road", "confidence": "probable", "note": "single patrol report"}, headers=AN)
    assert disp.status_code == 200, disp.text
    gid = disp.json()["created"]["id"]
    snap = client.get("/v1/cop/snapshot").json()
    g = next(x for x in snap["graphics"] if x["id"] == gid)
    assert g["type"] == "hostile_checkpoint" and g["threat_graphic"] is True and g["basis"] == f"report {r.json()['id']}"
    report = next(x for x in snap["s2_reports"] if x["id"] == r.json()["id"])
    assert report["status"] == "promoted" and report["disposition_target_id"] == gid
