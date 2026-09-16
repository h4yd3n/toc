"""Sigtoc plan Phase 2: RFIs, collection tasked from an NAI, the ISR sync view, pattern of life, and threshold rules."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
for k in ("ANTHROPIC_API_KEY", "TWILIO_AUTH_TOKEN", "TWILIO_ACCOUNT_SID", "SLACK_WEBHOOK_URL"): os.environ.pop(k, None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc_day"}
AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "s2_lee"}
EA = {"X-TOC-Role": "ea", "X-TOC-Actor": "ops_1"}
SEC = {"X-TOC-Role": "security", "X-TOC-Actor": "guard_7"}
GATE = {"lat": 37.7897, "lon": -122.3989, "place": "north gate, SF HQ"}  # 2.4 km from loc_sf, inside the seed surveillance point


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed").status_code == 200
        yield c


def _req_for(client, subject_id):
    return next(r for r in client.get("/v1/s2/requirements").json() if r["subject_id"] == subject_id)


def test_rfi_is_a_tasking_kind_s3_can_raise_on_s2(client):
    r = client.post("/v1/cop/taskings", json={"kind": "rfi", "title": "What is the protest picture around the London office on Monday?", "from_section": "S3", "to_section": "S2", "priority": "priority"}, headers=EA)
    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "rfi" and r.json()["status"] == "requested"
    assert client.post("/v1/cop/taskings", json={"kind": "rumour", "title": "x", "from_section": "S3", "to_section": "S2"}, headers=EA).status_code == 422


def test_collection_tasked_from_an_nai_moves_its_pirs_to_collecting(client):
    nai = _req_for(client, "loc_ldn")
    assert next(p for p in client.get("/v1/cop/snapshot").json()["pirs"] if p["id"] == "PIR-02")["status"] == "OPEN"
    body = {"kind": "collection", "title": f"Watch NAI — {nai['subject_name']}", "from_section": "S2", "to_section": "S3", "subject_type": "requirement", "subject_id": nai["id"],
            "subject_name": nai["subject_name"], "asset": "Guard force foot patrol, hourly", "priority": "priority", "notes": nai["question"]}
    r = client.post("/v1/cop/taskings", json=body, headers=AN)
    assert r.status_code == 201, r.text
    assert r.json()["pirs_collecting"] == ["PIR-02"]
    assert next(p for p in client.get("/v1/cop/snapshot").json()["pirs"] if p["id"] == "PIR-02")["status"] == "COLLECTING"
    log = client.get("/v1/cop/log", params={"limit": 5}).json()
    assert any(e["type"] == "cop.tasking.raised" for e in log)


def test_report_linked_to_an_nai_moves_its_pirs_to_collecting(client):
    nai = _req_for(client, "evt_002")
    assert next(p for p in client.get("/v1/cop/snapshot").json()["pirs"] if p["id"] == "PIR-04")["status"] == "OPEN"
    rid = client.post("/v1/s2/reports", json={"text": "Counter-protest permit filed for the strip on the keynote day.", "reported_by": "guard_7", "lat": nai["lat"], "lon": nai["lon"], "place": "venue perimeter"}, headers=SEC).json()["id"]
    r = client.post(f"/v1/s2/reports/{rid}/dispose", json={"action": "link", "target_type": "nai", "target_id": nai["id"]}, headers=AN)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "linked" and r.json()["created"] == {"object_type": "pirs", "collecting": ["PIR-04"]}
    assert next(p for p in client.get("/v1/cop/snapshot").json()["pirs"] if p["id"] == "PIR-04")["status"] == "COLLECTING"
    assert client.post(f"/v1/s2/reports/{rid}/dispose", json={"action": "link", "target_type": "nai", "target_id": "req_nope"}, headers=AN).status_code == 404


def test_isr_sync_view_lays_nais_against_days(client):
    v = client.get("/v1/s2/isr-sync", params={"days": 7, "ahead": 3}).json()
    assert len(v["days"]) == 10 and v["days"][6] == v["today"]
    assert v["nais"] and all(len(n["cells"]) == 10 for n in v["nais"])
    ldn = next(n for n in v["nais"] if n["subject_id"] == "loc_ldn")
    assert ldn["taskings"] and ldn["taskings"][0]["kind"] == "collection"
    today = next(c for c in ldn["cells"] if c["date"] == v["today"])
    assert ldn["taskings"][0]["id"] in today["tasked"] and today["covered"] and not today["future"]
    assert all(c["future"] for c in ldn["cells"][7:])
    assert v["taskings_open"] >= 1 and isinstance(v["gaps"], list)
    vegas = next(n for n in v["nais"] if n["subject_id"] == "evt_002")
    assert vegas["reports"] >= 1  # the report filed against it above


def test_pattern_of_life_counts_and_never_scores(client):
    p = client.get("/v1/s2/patterns", params={"days": 30}).json()
    sf = next(a for a in p["actors"] if a["id"] == "act_sf_surveillance")
    assert sf["sightings_total"] == 2 and sf["wheel"]["events"] == 2 and "of 2 events" in sf["wheel"]["pattern"] or sf["wheel"]["pattern"].startswith("no pattern")
    assert set(sf["wheel"]) >= {"grid", "days", "hours", "peak", "pattern"} and len(sf["wheel"]["grid"]) == 7
    dc = next(n for n in p["nais"] if n["subject_name"].startswith("DC") or n["id"] == "req_loc_loc_dc2")
    assert dc["sightings"] >= 1 and dc["actors"][0]["id"] == "act_dc_threat_cluster"
    assert p["since_intsum"] is None  # no INTSUM drafted in this module yet
    client.post("/v1/s2/intsum/draft", headers=BC)
    p2 = client.get("/v1/s2/patterns").json()
    assert p2["since_intsum"] and p2["since_intsum"]["sightings"] == 0


def test_threshold_rules_suggest_from_real_sightings_not_seed(client):
    assert client.post("/v1/s2/warnings/suggest").json()["suggested"] == []  # seed sightings are exercises and never count
    actor = client.post("/v1/s2/actors", json={"kind": "group", "name": "Grey sedan pair", "strength": "two people"}, headers=AN).json()
    for i in range(3):
        rid = client.post("/v1/s2/reports", json={"text": f"Grey sedan pair back at the north gate, pass {i + 1}.", "reported_by": "guard_7", **GATE}, headers=SEC).json()["id"]
        d = client.post(f"/v1/s2/reports/{rid}/dispose", json={"action": "link", "target_type": "actor", "target_id": actor["id"], "confidence": "probable"}, headers=AN)
        assert d.status_code == 200, d.text
    s = client.post("/v1/s2/warnings/suggest").json()["suggested"]
    by_basis = {w["suggested_by"]: w for w in s}
    assert "rule:3 sightings in 7 days" in by_basis and by_basis["rule:3 sightings in 7 days"]["subject_id"] == "loc_sf"
    assert "rule:actor within 5 km of site" in by_basis and by_basis["rule:actor within 5 km of site"]["threat_id"] == f"actor-near:{actor['id']}"
    assert all(w["status"] == "suggested" and w["severity"] == "elevated" for w in s)
    assert client.post("/v1/s2/warnings/suggest").json()["suggested"] == []  # idempotent
    # a corroborated report inside the seed surveillance-point graphic at the north gate
    rid = client.post("/v1/s2/reports", json={"text": "Camera confirms the sedan at the surveillance point.", "reported_by": "guard_7", **GATE}, headers=SEC).json()["id"]
    assert client.post("/v1/s2/warnings/suggest").json()["suggested"] == []  # filed is not enough
    client.post(f"/v1/s2/reports/{rid}/dispose", json={"action": "corroborate", "note": "camera"}, headers=AN)
    s = client.post("/v1/s2/warnings/suggest").json()["suggested"]
    assert len(s) == 1 and s[0]["suggested_by"] == "rule:corroborated report inside threat graphic" and s[0]["threat_id"].startswith("graphic:")


def test_thresholds_are_settings(monkeypatch):
    from sigtoc.warning import thresholds
    monkeypatch.setenv("TOC_S2_SIGHTING_THRESHOLD", "5"); monkeypatch.setenv("TOC_S2_SIGHTING_DAYS", "14"); monkeypatch.setenv("TOC_S2_SITE_BUFFER_KM", "2")
    assert thresholds() == {"sightings": 5, "days": 14, "site_km": 2.0}
