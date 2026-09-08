"""Synthetic administrative manifests: no production provider or operational data."""
import asyncio
import io
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from coptoc.app import app
from coptoc import ingestion as ingest
from coptoc.sections import ShipmentRow
from sigtoc.api import sessions

BC={'X-TOC-Role':'battle_captain','X-TOC-Actor':'Test reviewer'}
S4={'X-TOC-Role':'logistics','X-TOC-Actor':'Test logistics'}
AN={'X-TOC-Role':'analyst'}

@pytest.fixture(autouse=True)
def no_worker(monkeypatch):
    monkeypatch.setenv('TOC_AI_WORKER','off')
    monkeypatch.setenv('TOC_OFFLINE','1')
    monkeypatch.setenv('TOC_AI_PROVIDER','off')


def destination(c):
    return next(l['id'] for l in c.get('/v1/cop/snapshot',headers=BC).json()['locations'] if l['sensitivity']!='restricted')


def existing(c,loc,ref):
    r=c.post('/v1/cop/shipments',headers=BC,json={'description':'Office paper delivery','quantity':'10 boxes','ref':ref,'to_location_id':loc,'eta':'2026-09-09T16:00:00Z'})
    assert r.status_code==201,r.text
    return r.json()['id']


def extractor(monkeypatch, values, *, questions=None, invalid=False):
    async def fake(response_type,instruction,payload):
        quote=payload['pages'][0]['text'] if not invalid else 'INVENTED SOURCE'
        return ingest.Manifest(shipments=[ingest.ExtractedShipment(fields=[ingest.ExtractedField(field=k,value=v,page=1,quote=quote) for k,v in values.items()],questions=questions or [])],gaps=[]),{'provider':'test','model':'synthetic-fixture','metrics':{}}
    monkeypatch.setattr(ingest,'model_structured',fake)


def submit(c,loc,text):
    response=c.post('/v1/intake/text',headers=S4,json={'location_id':loc,'text':text})
    assert response.status_code==201,response.text
    return response.json()['id']


def process(c,sid):
    asyncio.run(ingest.ingestion_tick())
    return c.get('/v1/intake/'+sid,headers=S4).json()


def decide(c,sid,p,action,**kwargs):
    return c.patch(f'/v1/intake/{sid}/proposals/{p["id"]}',headers=S4,json={'revision':p['revision'],'action':action,**kwargs})


def test_extract_review_apply_and_replay(monkeypatch):
    with TestClient(app) as c:
        loc=destination(c);ref='PAPER-'+uuid.uuid4().hex;target=existing(c,loc,ref)
        text=f'{ref}: Office paper delivery now 12 boxes; ETA 2026-09-10T16:00:00Z.'
        extractor(monkeypatch,{'ref':ref,'quantity':'12 boxes','eta':'2026-09-10T16:00:00Z'})
        sid=submit(c,loc,text);data=process(c,sid);assert data['status']=='review',data
        p=data['proposals'][0];assert p['target_id']==target and p['status']=='ready'
        before=next(s for s in c.get('/v1/cop/snapshot').json()['s4']['shipments'] if s['id']==target)
        assert before['quantity']=='10 boxes'
        applied=decide(c,sid,p,'apply');assert applied.status_code==200,applied.text
        assert applied.json()['status']=='applied'
        assert decide(c,sid,p,'apply').json()['status']=='applied'
        after=next(s for s in c.get('/v1/cop/snapshot').json()['s4']['shipments'] if s['id']==target)
        assert after['quantity']=='12 boxes'
        assert submit(c,loc,text)==sid
        assert c.get('/v1/intake/'+sid+'/source',headers=S4).content==text.encode()
        assert any(h['action']=='record_applied' for h in applied.json()['history'])


def test_conflict_requires_fresh_comparison(monkeypatch):
    with TestClient(app) as c:
        loc=destination(c);ref='CONFLICT-'+uuid.uuid4().hex;target=existing(c,loc,ref)
        extractor(monkeypatch,{'ref':ref,'quantity':'14 boxes'})
        sid=submit(c,loc,ref+' now 14 boxes');p=process(c,sid)['proposals'][0]
        assert c.patch('/v1/cop/shipments/'+target,headers=BC,json={'note':'A newer human update'}).status_code==200
        conflict=decide(c,sid,p,'apply').json();assert conflict['status']=='conflict'
        assert decide(c,sid,p,'apply').status_code==409
        saved=decide(c,sid,conflict,'save',note='Reviewed current record').json();assert saved['current']['note']=='A newer human update'
        applied=decide(c,sid,saved,'apply');assert applied.status_code==200,applied.text
        assert applied.json()['status']=='applied'


def test_new_requires_explicit_confirmation_and_duplicate_reference_conflicts(monkeypatch):
    with TestClient(app) as c:
        loc=destination(c);ref='NEW-'+uuid.uuid4().hex
        values={'description':'Printer paper','quantity':'4 boxes','ref':ref,'eta':'2026-09-11T12:00:00Z','status':'planned'}
        extractor(monkeypatch,values)
        sid=submit(c,loc,ref+' new paper delivery');p=process(c,sid)['proposals'][0]
        assert decide(c,sid,p,'apply').status_code in (409,422)
        saved=decide(c,sid,p,'save',create_new=True,note='Confirmed destination and new delivery').json()
        assert saved['status']=='ready'
        existing(c,loc,ref)
        conflict=decide(c,sid,saved,'apply');assert conflict.status_code==200,conflict.text
        assert conflict.json()['status']=='conflict'


def test_create_new_and_reject_independent_proposal(monkeypatch):
    with TestClient(app) as c:
        loc=destination(c);ref='CREATE-'+uuid.uuid4().hex
        values={'description':'Office stationery','ref':ref,'eta':'2026-09-11T12:00:00Z','status':'planned'}
        extractor(monkeypatch,values)
        sid=submit(c,loc,ref+' stationery delivery');p=process(c,sid)['proposals'][0]
        saved=decide(c,sid,p,'save',create_new=True,note='New delivery confirmed').json()
        result=decide(c,sid,saved,'apply');assert result.status_code==200,result.text
        assert result.json()['status']=='applied'
        assert len([s for s in c.get('/v1/cop/snapshot').json()['s4']['shipments'] if s['ref']==ref])==1
        sid2=submit(c,loc,ref+' unrelated correction');p2=process(c,sid2)['proposals'][0]
        # Same field values are now unchanged; no new approval burden.
        assert p2['status']=='unchanged'


def test_invalid_citation_and_unconfigured_provider_fail_visibly(monkeypatch):
    with TestClient(app) as c:
        loc=destination(c)
        sid=submit(c,loc,'Synthetic office manifest '+uuid.uuid4().hex)
        assert process(c,sid)['status']=='failed'
        extractor(monkeypatch,{'description':'Office delivery'},invalid=True)
        assert c.post('/v1/intake/'+sid+'/retry',headers=S4).status_code==200
        failed=process(c,sid);assert failed['status']=='failed' and not failed['proposals']


def test_permissions_before_and_after_extraction(monkeypatch):
    from coptoc.db_models import LocationRow
    with TestClient(app) as c:
        loc=destination(c);ref='PRIVATE-'+uuid.uuid4().hex
        assert c.post('/v1/intake/text',headers=AN,json={'text':'Office update','location_id':loc}).status_code==403
        sid=submit(c,loc,ref+' office delivery')
        extractor(monkeypatch,{'description':'Office delivery'})
        data=process(c,sid)
        assert c.get('/v1/intake/'+sid,headers=AN).status_code==200
        assert c.get('/v1/intake/'+sid,headers={'X-TOC-Role':'signal'}).status_code==403
        async def restrict(value):
            async with sessions()() as s:
                l=await s.get(LocationRow,loc);l.sensitivity=value;await s.commit()
        asyncio.run(restrict('restricted'))
        try:
            assert c.get('/v1/intake/'+sid,headers=BC).status_code==403
            assert c.get('/v1/intake/'+sid+'/source',headers=BC).status_code==403
            assert not any(i['id']==sid for i in c.get('/v1/intake',headers=BC).json()['items'])
            assert decide(c,sid,data['proposals'][0],'reject').status_code==403
        finally:
            asyncio.run(restrict('public'))


def test_partial_review_keeps_other_items_pending(monkeypatch):
    async def fake(t,instruction,payload):
        fields=[ingest.ExtractedField(field='description',value='Office supplies',page=1,quote=payload['pages'][0]['text'])]
        return ingest.Manifest(shipments=[ingest.ExtractedShipment(fields=fields,questions=[]),ingest.ExtractedShipment(fields=fields,questions=[])],gaps=[]),{'provider':'test','model':'fixture'}
    monkeypatch.setattr(ingest,'model_structured',fake)
    with TestClient(app) as c:
        sid=submit(c,destination(c),'Two separate office deliveries '+uuid.uuid4().hex)
        data=process(c,sid);a,b=data['proposals'];assert decide(c,sid,a,'reject',note='Not needed').status_code==200
        fresh=c.get('/v1/intake/'+sid,headers=S4).json();assert fresh['pending']==1
        assert next(p for p in fresh['proposals'] if p['id']==b['id'])['status']=='needs_clarification'


def test_pdf_validation_and_extracted_source(monkeypatch):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject
    writer=PdfWriter();page=writer.add_blank_page(width=300,height=300)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 10 200 Td (Office supplies: 10 boxes.) Tj ET');page[NameObject('/Contents')]=writer._add_object(stream)
    buf=io.BytesIO();writer.write(buf)
    with TestClient(app) as c:
        loc=destination(c)
        r=c.post('/v1/intake/file',headers=S4,data={'location_id':loc},files={'file':('manifest.pdf',buf.getvalue(),'application/pdf')})
        assert r.status_code==201,r.text
        assert '10 boxes' in r.json()['pages'][0]['text']
        assert process(c, r.json()['id'])['status'] == 'failed'  # Provider is off; leave no queued fixture.
        assert c.post('/v1/intake/file',headers=S4,data={'location_id':loc},files={'file':('fake.pdf',b'not a pdf','application/pdf')}).status_code==422
        blank=PdfWriter();blank.add_blank_page(width=100,height=100);b=io.BytesIO();blank.write(b)
        assert c.post('/v1/intake/file',headers=S4,data={'location_id':loc},files={'file':('scan.pdf',b.getvalue(),'application/pdf')}).status_code==422
        assert c.post('/v1/intake/file',headers=S4,data={'location_id':loc},files={'file':('large.pdf',b'x'*(ingest.MAX_BYTES+1),'application/pdf')}).status_code==413


def test_administrative_monitor_deduplicates_and_respects_dismissal():
    from coptoc.intake_monitor import monitor_tick
    with TestClient(app) as c:
        loc=destination(c);ref='OVERDUE-'+uuid.uuid4().hex;target=existing(c,loc,ref)
        c.patch('/v1/cop/shipments/'+target,headers=BC,json={'eta':'2020-01-01T12:00:00Z'})
        asyncio.run(monitor_tick())
        board=c.get('/v1/intake/monitor/findings',headers=S4);assert board.status_code==200,board.text
        item=next(i for i in board.json()['items'] if i['shipment_id']==target)
        path='/v1/intake/monitor/findings/'+item['id']
        assert c.patch(path,headers=S4,json={'revision':item['revision'],'action':'dismiss','note':'Awaiting receipt confirmation'}).status_code==200
        asyncio.run(monitor_tick())
        new=next(i for i in c.get('/v1/intake/monitor/findings',headers=S4).json()['items'] if i['id']==item['id'])
        assert new['status']=='dismissed'
        assert c.patch(path,headers=S4,json={'revision':item['revision'],'action':'reopen','note':'Stale review'}).status_code==409
        c.patch('/v1/cop/shipments/'+target,headers=BC,json={'status':'arrived'})
        asyncio.run(monitor_tick())
        done=next(i for i in c.get('/v1/intake/monitor/findings',headers=S4).json()['items'] if i['id']==item['id'])
        assert done['status']=='resolved'
        assert c.get('/v1/intake/monitor/findings',headers={'X-TOC-Role':'signal'}).status_code==403


def test_reference_claim_is_unique_and_case_insensitive():
    async def check():
        async with sessions()() as s:
            assert await ingest.claim_reference(s,'synthetic-location','Office-Reference','shipment-a')
            await s.commit()
        async with sessions()() as s:
            assert not await ingest.claim_reference(s,'synthetic-location','OFFICE-REFERENCE','shipment-b')
            assert await ingest.claim_reference(s,'synthetic-location','office-reference','shipment-a')
    with TestClient(app):
        asyncio.run(check())


def test_owner_revoked_while_provider_runs(monkeypatch):
    from coptoc.db_models import LocationRow
    async def revoked(t,instruction,payload):
        async with sessions()() as s:
            loc=await s.get(LocationRow,location_id);loc.sensitivity='restricted';await s.commit()
        return ingest.Manifest(shipments=[],gaps=[]),{'provider':'test','model':'fixture'}
    monkeypatch.setattr(ingest,'model_structured',revoked)
    with TestClient(app) as c:
        location_id=destination(c);sid=submit(c,location_id,'Synthetic revocation source '+uuid.uuid4().hex)
        asyncio.run(ingest.ingestion_tick())
        async def inspect_restore():
            async with sessions()() as s:
                row=await s.get(ingest.SubmissionRow,sid)
                assert row.status=='failed'
                assert not (await s.scalars(select(ingest.ProposalRow).where(ingest.ProposalRow.submission_id==sid))).all()
                loc=await s.get(LocationRow,location_id);loc.sensitivity='public';await s.commit()
        asyncio.run(inspect_restore())
