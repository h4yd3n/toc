"""§5.10 #4: dissemination is tracked — recipients, acknowledgements, latency, and the unread warning on the INTSUM."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None); os.environ.pop("SLACK_WEBHOOK_URL", None)

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
        yield c


def test_only_released_products_go_out_and_the_record_shows_who_got_it(client):
    assert client.post("/v1/s2/products/assessment/ASMT-015/disseminate", json={"recipients": ["ep"]}, headers=AN).status_code == 409  # in review
    assert client.post("/v1/s2/products/assessment/ASMT-014/disseminate", json={"recipients": ["ep"]}, headers=EP).status_code == 403
    r = client.post("/v1/s2/products/assessment/ASMT-014/disseminate", json={"recipients": ["ep", "security", "ep_lead"], "channel": "chat", "note": "read before wheels up"}, headers=AN)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["sent"] == 3 and d["acknowledged"] == 0 and set(d["unacknowledged"]) == {"ep", "security", "ep_lead"}
    assert all(x["delivery"] == "simulated" and x["channel"] == "chat" for x in d["recipients"])  # no Slack in tests: says so
    assert d["recipients"][0]["latency"]["created_to_sent_min"] is not None and d["recipients"][0]["latency"]["sent_to_ack_min"] is None


def test_acknowledgement_matches_by_actor_or_role_and_records_latency(client):
    d = client.post("/v1/s2/products/assessment/ASMT-014/ack", headers=EP).json()  # ep_lead matches by actor first
    acked = [x for x in d["recipients"] if x["acknowledged_at"]]
    assert len(acked) == 1 and acked[0]["recipient"] == "ep_lead" and acked[0]["acknowledged_by"] == "ep_lead" and acked[0]["latency"]["sent_to_ack_min"] == 0
    d = client.post("/v1/s2/products/assessment/ASMT-014/ack", headers={"X-TOC-Role": "ep", "X-TOC-Actor": "ep_2"}).json()  # second EP matches the role row
    assert d["acknowledged"] == 2 and d["unacknowledged"] == ["security"]
    d = client.post("/v1/s2/products/assessment/ASMT-014/ack", headers={"X-TOC-Role": "ea", "X-TOC-Actor": "EA"}).json()  # not on the list: unsolicited read, still on the record
    assert d["sent"] == 4 and any(x["note"] == "unsolicited read" and x["recipient"] == "EA" for x in d["recipients"])
    types = [e["type"] for e in client.get("/v1/cop/log", params={"limit": 8}).json()]
    assert "s2.product.acknowledged" in types and "s2.product.disseminated" in types


def test_unread_warnings_surface_on_the_intsum(client):
    import asyncio
    from datetime import timedelta
    from sigtoc.api import sessions
    from sigtoc.dissemination import DistributionRow
    from sqlalchemy import select
    async def age():
        async with sessions()() as s:
            for r in (await s.execute(select(DistributionRow).where(DistributionRow.recipient == "security"))).scalars():
                r.sent_at = r.sent_at - timedelta(hours=3)
            await s.commit()
    asyncio.run(age())
    assert client.get("/v1/s2/products/unacknowledged").json()[0]["recipient"] == "security"
    d = client.post("/v1/s2/intsum/draft", headers=BC).json()
    assert d["products"]["unacknowledged"] and d["products"]["unacknowledged"][0]["recipient"] == "security" and d["products"]["unacknowledged"][0]["outstanding_min"] >= 180
    dist = client.get("/v1/s2/products/assessment/ASMT-014/distribution").json()
    assert dist["stale"] == ["security"]
    # an INTSUM, once released, is itself disseminated the same way
    client.post(f"/v1/s2/intsum/{d['id']}/release", json={}, headers=BC)
    r = client.post(f"/v1/s2/products/intsum/{d['id']}/disseminate", json={"recipients": ["battle_captain", "ep"]}, headers=BC)
    assert r.status_code == 201 and r.json()["sent"] == 2
