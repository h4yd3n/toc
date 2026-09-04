"""§5.6 INTSUM (Decision G): a diff since the last one, fixed structure, drafted at a fixed hour, released by the Battle Captain only."""
import os, tempfile, asyncio
from datetime import datetime, timedelta, timezone
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_INTSUM_CLOCK"] = "off"  # the fixed-time INTSUM draft is tested directly, not on a timer
os.environ["TOC_OFFLINE"] = "1"  # collectors and the holiday lookup never touch the network in tests
os.environ.pop("ANTHROPIC_API_KEY", None); os.environ.pop("TOC_DRAFTER", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc_day"}
AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "s2_lee"}
SEC = {"X-TOC-Role": "security", "X-TOC-Actor": "guard_07"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        c.post("/v1/s2/requirements/sync", json=c.get("/v1/cop/snapshot", params={"restricted": "true"}, headers=BC).json())
        yield c


def test_intsum_is_a_diff_in_fixed_order(client):
    assert client.get("/v1/s2/intsum/latest").status_code == 404
    assert client.post("/v1/s2/intsum/draft", headers=SEC).status_code == 403
    # something happens on the wall in the period: a posture change, a confirmed link, an organic report
    client.patch("/v1/cop/locations/loc_sgp/posture", json={"posture": "elevated", "reason": "regional advisory"}, headers=BC)
    client.post("/v1/cop/threats/thr_004/links", json={"target_type": "location", "target_id": "loc_dc2", "note": "corroborated"}, headers=AN)
    client.post("/v1/s2/reports", json={"text": "Crowd of ~40 forming at the SF lobby entrance, signs, no police yet.", "reported_by": "guard_07", "place": "SF HQ lobby"}, headers=SEC)
    d = client.post("/v1/s2/intsum/draft", headers=AN).json()
    assert d["status"] == "draft" and d["nstr"] is False and d["period"]["hours"] == 24.0
    assert d["structure"] == ["headline", "requirements", "new_threats", "wall", "reports_and_cases", "products", "collection"]
    assert d["requirements"]["active"] >= 20 and d["requirements"]["directed"] == 2
    # seeded threats observed inside the last 24 h are "new", each attributed to the requirements it falls inside, P1 first
    ids = {t["id"] for t in d["new_threats"]}
    assert "thr_001" in ids and "thr_004" in ids
    riyadh = next(t for t in d["new_threats"] if t["id"] == "thr_001")
    assert riyadh["requirements"] and riyadh["requirements"][0]["priority"] == 1 and "Riyadh" in riyadh["requirements"][0]["subject"]
    assert d["new_threats"][0]["severity"] in ("critical", "elevated")  # worst first
    # the ledger engine is shared across test modules, so look for our own events rather than exact counts
    assert any(e["actor"] == "bc_day" for e in d["wall"]["posture"]) and any(e["actor"] == "s2_lee" for e in d["wall"]["links"])
    crowd = next(r for r in d["reports"] if "Crowd" in r["text"])  # the seeded SPOTREP from last night is in the period too
    assert crowd["grade"] == "A2" and crowd["case_id"] is None
    assert d["collection"]["gaps"][0]["requirements_affected"] >= 10 and d["collection"]["sources"]
    assert "new threat" in d["headline"] and "posture change" in d["headline"]


def test_next_intsum_starts_where_the_last_ended_and_nstr_is_honest(client):
    prev = client.get("/v1/s2/intsum/latest").json()
    d = client.post("/v1/s2/intsum/draft", headers=BC).json()
    assert d["period"]["from"] == prev["period"]["to"]
    assert d["new_threats"] == [] and d["reports"] == []
    # the only thing that happened since is the previous draft itself, which is not significant
    assert d["nstr"] is True and d["headline"].startswith("NSTR")


def test_release_is_the_battle_captains_alone(client):
    d = client.get("/v1/s2/intsum/latest").json()
    assert client.post(f"/v1/s2/intsum/{d['id']}/release", json={}, headers=AN).status_code == 403
    r = client.post(f"/v1/s2/intsum/{d['id']}/release", json={"notes": "Read at Dublin handover."}, headers=BC)
    assert r.status_code == 200 and r.json()["status"] == "released" and r.json()["released_by"] == "bc_day"
    assert client.post(f"/v1/s2/intsum/{d['id']}/release", json={}, headers=BC).status_code == 409
    lst = client.get("/v1/s2/intsum").json()
    assert lst[0]["id"] == d["id"] and lst[0]["status"] == "released" and len(lst) == 2
    types = {e["type"] for e in client.get("/v1/cop/log", params={"limit": 10}).json()}
    assert "s2.intsum.released" in types


def test_fixed_time_draft_is_idempotent_per_day(client):
    from sigtoc.api import draft_if_due, sessions
    from sigtoc.intsum import DRAFT_HOUR_UTC
    async def run(now):
        async with sessions()() as s:
            return await draft_if_due(s, now)
    today = datetime.now(timezone.utc).replace(tzinfo=None, hour=DRAFT_HOUR_UTC, minute=1, second=0, microsecond=0)
    # today's already exists (drafted above), so the clock does nothing
    assert asyncio.run(run(today)) is None
    # tomorrow at the hour: drafts once, then not again
    tomorrow = today + timedelta(days=1)
    row = asyncio.run(run(tomorrow))
    assert row is not None and row.period_to == tomorrow
    assert asyncio.run(run(tomorrow + timedelta(minutes=10))) is None
    # before the hour the next day: nothing
    assert asyncio.run(run(tomorrow + timedelta(days=1) - timedelta(hours=1) if DRAFT_HOUR_UTC > 0 else tomorrow + timedelta(days=1, minutes=-1))) is None or DRAFT_HOUR_UTC == 0
