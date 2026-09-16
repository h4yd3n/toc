"""Sigtoc plan Phase 3: IPB, threat COAs, decision points and the DSM, the intelligence estimate, and the annex to an operation."""
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
STATE = {}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed").status_code == 200
        yield c


def test_a_coa_takes_an_icd_203_word_not_a_number(client):
    body = {"title": "Sedan pair escalates to a forced entry at the north gate", "subject_type": "location", "subject_id": "loc_sf", "actor_id": "act_sf_surveillance",
            "indicators": ["vehicle staged with engine running", "third person joins the pair"], "nai_ids": ["req_loc_loc_sf"]}
    assert client.post("/v1/s2/coas", json={**body, "likelihood": "70%"}, headers=AN).status_code == 422
    assert client.post("/v1/s2/coas", json={**body, "likelihood": "likely", "most_likely": True}, headers=SEC).status_code == 403
    assert client.post("/v1/s2/coas", json={**body, "most_dangerous": True}, headers=AN).status_code == 422  # a flag needs a likelihood
    r = client.post("/v1/s2/coas", json={**body, "likelihood": "unlikely", "confidence": "moderate", "most_dangerous": True}, headers=AN)
    assert r.status_code == 201, r.text
    STATE["md"] = r.json()["id"]
    assert r.json()["status"] == "assessed" and r.json()["actor_name"] and r.json()["most_dangerous"] is True


def test_ipb_drafts_candidates_from_assessed_intent_and_waits_on_the_analyst(client):
    r = client.post("/v1/s2/ipb/draft", json={"subject_type": "location", "subject_id": "loc_sf"}, headers=AN)
    assert r.status_code == 201, r.text
    d = r.json(); p = d["product"]
    STATE["ipb"] = d["id"]
    assert d["kind"] == "ipb" and d["status"] == "draft" and d["drafted_by"] == "rule:ipb"
    assert any(n["id"] == "req_loc_loc_sf" for n in p["step1_area"]["nais"]) and any(l["id"] == "loc_sf" for l in p["step1_area"]["sites"])
    sf = next(a for a in p["step3_threat"]["actors"] if a["id"] == "act_sf_surveillance")
    assert sf["sightings"] == 2 and sf["assessed_intent"] and "pattern" in sf
    assert any(g["type"] == "surveillance_detection_point" for g in p["step3_threat"]["threat_graphics"])
    # the sedan pair carries an assessed intent but already has a COA from the analyst, so no candidate for it; the DC cluster is not in the SF area
    cands = [c for c in p["step4_coas"] if c["status"] == "candidate"]
    assert not cands or all(c["actor_id"] != "act_sf_surveillance" for c in cands)
    assert any(c["id"] == STATE["md"] for c in p["step4_coas"])
    assert p["event_template"] and p["event_template"][0]["nai_name"] and p["citations"] and "act_sf_surveillance" in p["citations"]
    assert "number" not in " ".join(p["gaps"]).lower() and p["note"].startswith("Drafted by rule")


def test_candidates_block_approval_until_assessed(client):
    # an actor with intent and no COA yet: create one in the area, redraft, and see the candidate appear and block
    a = client.post("/v1/s2/actors", json={"kind": "individual", "name": "Bay Bridge drone hobbyist", "assessed_intent": "Overflying the roof line to film the executive floor", "lat": 37.79, "lon": -122.40, "place": "Embarcadero"}, headers=AN).json()
    d = client.post("/v1/s2/ipb/draft", json={"subject_type": "location", "subject_id": "loc_sf"}, headers=AN).json()
    cand = next(c for c in d["new_candidates"] if c["actor_id"] == a["id"])
    assert cand["status"] == "candidate" and cand["likelihood"] == "unassessed" and "Overflying" in cand["title"]
    assert any("Candidate COAs await" in g for g in d["product"]["gaps"])
    blocked = client.patch(f"/v1/s2/staff-products/{d['id']}", json={"status": "approved"}, headers=AN)
    assert blocked.status_code == 409 and "unassessed" in blocked.text
    assert client.get(f"/v1/s2/staff-products/{d['id']}").json()["blockers"] == ["candidate COAs are unassessed"]
    assert client.patch(f"/v1/s2/coas/{cand['id']}", json={"most_likely": True}, headers=AN).status_code == 422
    ok = client.patch(f"/v1/s2/coas/{cand['id']}", json={"likelihood": "very unlikely", "confidence": "low", "status": "rejected"}, headers=AN)
    assert ok.status_code == 200 and ok.json()["status"] == "rejected"
    ml = client.patch(f"/v1/s2/coas/{STATE['md']}", json={"most_likely": True}, headers=AN).json()
    assert ml["most_likely"] and ml["most_dangerous"]
    r = client.patch(f"/v1/s2/staff-products/{d['id']}", json={"status": "approved"}, headers=AN)
    assert r.status_code == 200 and r.json()["status"] == "approved" and r.json()["decided_by"] == "s2_lee"
    STATE["ipb"] = d["id"]
    # a second draft does not duplicate the candidate
    d2 = client.post("/v1/s2/ipb/draft", json={"subject_type": "location", "subject_id": "loc_sf"}, headers=AN).json()
    assert d2["new_candidates"] == []


def test_decision_points_join_into_the_dsm(client):
    op = client.post("/v1/cop/operations", json={"subject_type": "location", "subject_id": "loc_sf", "title": "Harden SF HQ north gate"}, headers=BC)
    assert op.status_code == 201, op.text
    STATE["op"] = op.json()["id"]
    pir = client.post("/v1/cop/pirs", json={"question": "Will the sedan pair return with a third person?", "subject_type": "location", "subject_id": "loc_sf"}, headers=AN)
    assert pir.status_code == 201, pir.text
    body = {"title": "DP 1 — close the north gate", "subject_type": "operation", "subject_id": STATE["op"], "decision": "Close the north gate and route staff through the garage",
            "trigger": "third person joins the pair, or vehicle staged with engine running", "pir_id": pir.json()["id"], "nai_ids": ["req_loc_loc_sf"], "coa_ids": [STATE["md"]],
            "action": "S1 posts a guard, S3 re-routes the executive movement", "owner_section": "S3", "latest_time": "2026-09-17T14:00:00Z"}
    assert client.post("/v1/s2/decision-points", json=body, headers=SEC).status_code == 403
    r = client.post("/v1/s2/decision-points", json=body, headers=EA)
    assert r.status_code == 201, r.text
    dp = r.json(); STATE["dp"] = dp["id"]
    assert dp["operation_id"] == STATE["op"] and dp["status"] == "open" and dp["latest_time"].startswith("2026-09-17T14:00")
    m = client.get("/v1/s2/dsm", params={"operation_id": STATE["op"]}).json()
    assert m["open"] == 1 and m["rows"][0]["pir"]["question"].startswith("Will the sedan") and m["rows"][0]["nais"][0]["id"] == "req_loc_loc_sf" and m["rows"][0]["coas"][0]["likelihood"] == "unlikely"
    assert client.patch(f"/v1/s2/decision-points/{dp['id']}", json={"status": "triggered"}, headers=BC).status_code == 422  # needs a note
    t = client.patch(f"/v1/s2/decision-points/{dp['id']}", json={"status": "triggered", "note": "guard_7 reports third person at 13:40Z"}, headers=BC)
    assert t.status_code == 200 and t.json()["status"] == "triggered" and t.json()["decided_by"] == "bc_day"
    assert client.get("/v1/s2/dsm", params={"operation_id": STATE["op"]}).json()["triggered"] == 1


def test_estimate_counts_and_annex_releases_only_on_approved_products(client):
    e = client.post("/v1/s2/intel-estimates/draft", json={"subject_type": "operation", "subject_id": STATE["op"]}, headers=AN)
    assert e.status_code == 201, e.text
    est = e.json(); p = est["product"]
    assert est["operation_id"] == STATE["op"] and p["mission"] == "Harden SF HQ north gate"
    assert any(s.startswith("Most likely:") and "unlikely" in s for s in p["conclusions"]) and any(s.startswith("PIRs:") for s in p["conclusions"])
    assert p["capabilities_coas"][0]["id"] == STATE["md"] and "act_sf_surveillance" in p["citations"]
    # an annex before the estimate is approved says what it is missing
    a1 = client.post(f"/v1/s2/operations/{STATE['op']}/annex", headers=AN).json()
    assert a1["kind"] == "annex" and a1["product"]["releasable"] is False and a1["product"]["missing"] == ["an approved intelligence estimate"]
    assert client.patch(f"/v1/s2/staff-products/{a1['id']}", json={"status": "released"}, headers=BC).status_code == 409
    assert client.patch(f"/v1/s2/staff-products/{est['id']}", json={"status": "approved"}, headers=AN).status_code == 200
    a2 = client.post(f"/v1/s2/operations/{STATE['op']}/annex", headers=AN).json()
    assert a2["product"]["releasable"] is True and a2["product"]["ipb"]["status"] == "approved" and a2["product"]["dsm"][0]["status"] == "triggered"
    assert a2["product"]["situation"] == p["conclusions"] and any(c["id"] == STATE["md"] for c in a2["product"]["coas"])
    assert client.patch(f"/v1/s2/staff-products/{a2['id']}", json={"status": "released"}, headers=AN).status_code == 403  # the Battle Captain releases
    assert client.patch(f"/v1/s2/staff-products/{a2['id']}", json={"status": "approved"}, headers=BC).status_code == 422  # released, not approved
    r = client.patch(f"/v1/s2/staff-products/{a2['id']}", json={"status": "released"}, headers=BC)
    assert r.status_code == 200 and r.json()["status"] == "released" and r.json()["product"]["released_by"] == "bc_day"
    assert client.get(f"/v1/s2/operations/{STATE['op']}/annex").json()["id"] == a2["id"]
    dist = client.post(f"/v1/s2/products/annex/{a2['id']}/disseminate", json={"recipients": ["battle_captain", "ea"]}, headers=BC)
    assert dist.status_code == 201, dist.text
    assert client.post(f"/v1/s2/products/annex/{a1['id']}/disseminate", json={"recipients": ["ea"]}, headers=BC).status_code == 409  # the draft does not go out
    heads = client.get("/v1/s2/staff-products", params={"operation_id": STATE["op"]}).json()
    assert {h["kind"] for h in heads} == {"estimate", "annex"} and all("product" not in h for h in heads)
    types = {e["type"] for e in client.get("/v1/cop/log", params={"limit": 40}).json()}
    assert {"s2.coa.created", "s2.dp.created", "s2.dp.updated", "s2.product.drafted", "s2.product.status"} <= types
