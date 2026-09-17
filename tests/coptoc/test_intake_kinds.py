"""§5.13 beyond S4: a communications status document read into S6's systems, and the retention rule that purges the
original once the decision has been made. Synthetic sources; no provider is called."""
import asyncio
import json
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from coptoc.app import app
from coptoc import ingestion as ingest
from coptoc.sections import SystemRow
from sigtoc.api import sessions

BC = {'X-TOC-Role': 'battle_captain', 'X-TOC-Actor': 'Test reviewer'}
S6 = {'X-TOC-Role': 'signal', 'X-TOC-Actor': 'Test signal'}
S4 = {'X-TOC-Role': 'logistics', 'X-TOC-Actor': 'Test logistics'}
NOTICE = ('Maintenance notice. TACSAT NET ALPHA at the site is DEGRADED from 0400Z while the antenna is re-pointed. '
          'It remains the primary net. Restoration expected within 6 hours.')


@pytest.fixture(autouse=True)
def no_worker(monkeypatch):
    monkeypatch.setenv('TOC_AI_WORKER', 'off')
    monkeypatch.setenv('TOC_OFFLINE', '1')
    monkeypatch.setenv('TOC_AI_PROVIDER', 'off')


def site(c):
    return next(l['id'] for l in c.get('/v1/cop/snapshot', headers=BC).json()['locations'] if l['sensitivity'] != 'restricted')


def extractor(monkeypatch, values, *, questions=None):
    async def fake(response_type, instruction, payload):
        quote = payload['pages'][0]['text']
        assert response_type is ingest.SystemReport, 'the system kind asks the provider for systems, not shipments'
        assert 'communications and system status' in instruction
        return ingest.SystemReport(systems=[ingest.ExtractedSystem(
            fields=[ingest.ExtractedSystemField(field=k, value=v, page=1, quote=quote) for k, v in values.items()],
            questions=questions or [])], gaps=[]), {'provider': 'test', 'model': 'synthetic-fixture', 'metrics': {}}
    monkeypatch.setattr(ingest, 'model_structured', fake)


def test_a_comms_notice_becomes_a_reviewed_system_change(monkeypatch):
    with TestClient(app) as c:
        loc = site(c)
        name = 'TACSAT NET ALPHA ' + uuid.uuid4().hex[:6]
        extractor(monkeypatch, {'name': name, 'status': 'degraded', 'pace': 'primary', 'note': 'Antenna re-pointing; restoration within 6 hours.'})
        # S4 owns shipments, not systems: the signal section owns this one
        assert c.post('/v1/intake/text', headers=S4, json={'location_id': loc, 'text': NOTICE, 'kind': 'system'}).status_code == 403
        sub = c.post('/v1/intake/text', headers=S6, json={'location_id': loc, 'text': NOTICE, 'kind': 'system'})
        assert sub.status_code == 201, sub.text
        sid = sub.json()['id']
        assert sub.json()['kind'] == 'system'
        asyncio.run(ingest.ingestion_tick())
        detail = c.get('/v1/intake/' + sid, headers=S6).json()
        assert detail['status'] == 'review' and len(detail['proposals']) == 1
        p = detail['proposals'][0]
        assert p['values']['status'] == 'degraded' and p['values']['pace'] == 'primary'
        assert all(e['quote'] in NOTICE for e in p['evidence'])
        # nothing is applied without a confirmed creation and a human note
        assert p['status'] == 'needs_clarification'
        premature = c.patch(f'/v1/intake/{sid}/proposals/{p["id"]}', headers=S6, json={'revision': p['revision'], 'action': 'apply', 'note': 'looks right'})
        assert premature.status_code == 422 and 'creation confirmation' in premature.json()['detail']
        saved = c.patch(f'/v1/intake/{sid}/proposals/{p["id"]}', headers=S6,
                        json={'revision': p['revision'], 'action': 'save', 'create_new': True, 'note': 'New net, confirmed with the signal NCO'})
        assert saved.status_code == 200, saved.text
        assert saved.json()['status'] == 'ready'
        applied = c.patch(f'/v1/intake/{sid}/proposals/{p["id"]}', headers=S6, json={'revision': saved.json()['revision'], 'action': 'apply', 'note': 'Approved'})
        assert applied.status_code == 200, applied.text
        assert applied.json()['status'] == 'applied'
        # the system is on the S6 board, at the site, with the source naming the submission
        board = c.get('/v1/cop/snapshot', headers=BC).json()['s6']['systems']
        made = next(x for x in board if x['name'] == name)
        assert made['status'] == 'degraded' and made['pace'] == 'primary'
        row = asyncio.run(_system_row(made['id']))
        assert row.source == 'intake:' + sid and row.location_id == loc and row.category == 'comms'


async def _system_row(sid):
    async with sessions()() as session:
        return await session.get(SystemRow, sid)


def test_each_section_sees_only_its_own_submissions(monkeypatch):
    with TestClient(app) as c:
        loc = site(c)
        extractor(monkeypatch, {'name': 'HF RETRANS ' + uuid.uuid4().hex[:6], 'status': 'down'})
        sid = c.post('/v1/intake/text', headers=S6, json={'location_id': loc, 'text': NOTICE, 'kind': 'system'}).json()['id']
        s6_board = c.get('/v1/intake', headers=S6).json()
        assert any(i['id'] == sid for i in s6_board['items'])
        assert [k['id'] for k in s6_board['kinds']] == ['system'], 'signal sees the system kind only'
        s4_board = c.get('/v1/intake', headers=S4).json()
        assert not any(i['id'] == sid for i in s4_board['items'])
        assert [k['id'] for k in s4_board['kinds']] == ['shipment']
        assert c.get('/v1/intake/' + sid, headers=S4).status_code == 403
        assert c.get('/v1/intake?kind=system', headers=S4).status_code == 403
        # the Battle Captain sees both kinds
        assert {k['id'] for k in c.get('/v1/intake', headers=BC).json()['kinds']} == {'shipment', 'system'}


def test_the_original_is_purged_on_the_retention_rule_and_the_decision_is_kept(monkeypatch):
    with TestClient(app) as c:
        loc = site(c)
        extractor(monkeypatch, {'name': 'SIPR TERMINAL ' + uuid.uuid4().hex[:6], 'status': 'up'})
        sid = c.post('/v1/intake/text', headers=S6, json={'location_id': loc, 'text': NOTICE, 'kind': 'system'}).json()['id']
        asyncio.run(ingest.ingestion_tick())
        assert c.get('/v1/intake/' + sid + '/source', headers=S6).content == NOTICE.encode()
        assert c.get('/v1/intake/' + sid, headers=S6).json()['source_available'] is True
        asyncio.run(_age(sid, ingest.retention_days() + 1))
        assert asyncio.run(_purge()) >= 1
        detail = c.get('/v1/intake/' + sid, headers=S6).json()
        assert detail['source_available'] is False and detail['purged_at']
        assert detail['pages'] == [] and detail['proposals'], 'the proposals and their quotations survive the purge'
        assert all(e['quote'] for e in detail['proposals'][0]['evidence'])
        gone = c.get('/v1/intake/' + sid + '/source', headers=S6)
        assert gone.status_code == 410 and 'retention' in gone.json()['detail']


async def _age(sid, days):
    async with sessions()() as session:
        row = await session.get(ingest.SubmissionRow, sid)
        row.created_at = row.created_at - timedelta(days=days)
        await session.commit()


async def _purge():
    async with sessions()() as session:
        return await ingest.purge_originals(session)
