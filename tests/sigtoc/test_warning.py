"""§5.6 Warning: collection suggests by rule, the Battle Captain releases, S6 carries it, the read-back is tracked."""
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
EP = {"X-TOC-Role": "ep", "X-TOC-Actor": "ep_lead"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        import asyncio
        from sqlalchemy import delete
        from sigtoc.api import sessions
        from sigtoc.intsum import IntsumRow
        async def clear():  # the engine is shared across modules; another module leaves an INTSUM dated tomorrow
            async with sessions()() as s:
                await s.execute(delete(IntsumRow)); await s.commit()
        asyncio.run(clear())
        yield c


def test_rule_suggests_from_confirmed_elevated_and_live_critical(client):
    assert client.post("/v1/s2/warnings/suggest").json()["suggested"] == []  # seed: nothing critical, no elevated confirmed link
    client.post("/v1/cop/threats/thr_004/links", json={"target_type": "location", "target_id": "loc_dc2", "note": "corroborated"}, headers=AN)  # elevated, now confirmed
    s = client.post("/v1/s2/warnings/suggest").json()["suggested"]
    assert len(s) == 1 and s[0]["subject_id"] == "loc_dc2" and s[0]["status"] == "suggested" and s[0]["suggested_by"] == "rule:confirmed link"
    assert client.post("/v1/s2/warnings/suggest").json()["suggested"] == []  # idempotent
    snap = client.get("/v1/cop/snapshot", headers=BC).json()
    assert snap["summary"]["warnings_pending"] == 1 and snap["summary"]["flash"] == 0 and snap["warnings"][0]["title"].startswith("FLASH")


def test_only_the_battle_captain_releases_and_release_dispatches(client):
    w = client.get("/v1/s2/warnings", params={"status": "suggested"}).json()[0]
    assert client.post(f"/v1/s2/warnings/{w['id']}/release", headers=AN).status_code == 403
    r = client.post(f"/v1/s2/warnings/{w['id']}/release", headers=BC)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "released" and d["released_by"] == "bc_day" and d["dispatch"]["people"] >= 1 and d["dispatch"]["simulated"] is True
    assert d["dispatch"]["sms"]["simulated"] + d["dispatch"]["sms"]["failed"] == d["dispatch"]["people"]  # no Twilio: simulated (or failed for no phone)
    snap = client.get("/v1/cop/snapshot", headers=BC).json()
    assert snap["summary"]["flash"] == 1
    dist = client.get(f"/v1/s2/products/warning/{w['id']}/distribution").json()
    assert set(dist["unacknowledged"]) == {"battle_captain", "ep", "security"}
    ack = client.post(f"/v1/s2/products/warning/{w['id']}/ack", headers=EP).json()
    assert ack["acknowledged"] == 1 and "ep" not in ack["unacknowledged"]
    assert client.post(f"/v1/s2/warnings/{w['id']}/release", headers=BC).status_code == 409
    types = {e["type"] for e in client.get("/v1/cop/log", params={"limit": 10}).json()}
    assert {"s2.warning.suggested", "s2.warning.released", "s2.product.acknowledged"} <= types


def test_human_draft_cancel_and_intsum_carries_warnings(client):
    assert client.post("/v1/s2/warnings", json={"subject_type": "event", "subject_id": "evt_002", "title": "Credible bomb threat to venue", "severity": "critical"}, headers=EP).status_code == 403
    d = client.post("/v1/s2/warnings", json={"subject_type": "event", "subject_id": "evt_002", "title": "Credible bomb threat to venue", "text": "LVMPD advises.", "severity": "critical"}, headers=AN).json()
    assert d["status"] == "draft" and d["title"] == "FLASH — Credible bomb threat to venue" and d["subject_name"] == "Global Sales Kickoff"
    assert client.post(f"/v1/s2/warnings/{d['id']}/cancel", headers=BC).json()["status"] == "cancelled"
    i = client.post("/v1/s2/intsum/draft", headers=BC).json()
    assert len(i["products"]["warnings"]) >= 2 and i["nstr"] is False
