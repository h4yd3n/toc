"""§5.12's remaining plan items, the buildable ones: typed graph proposals a human applies, repeat suppression across
assignments, assignments scoped to an operation or a requirement, and matching a report to the case it belongs to."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from sigtoc.api import standalone_app
from sigtoc import work

AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "Analyst"}
BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "Captain"}
TEXT = "Marcus Vane met Dana Ortiz at the north gate at 21:40 and left in a grey sedan."


def case_with_report(c, title="Graph proposals"):
    case = c.post('/v1/s2/cases', headers=AN, json={'title': title, 'kind': 'person'}).json()
    report = c.post('/v1/s2/reports', headers=AN, json={'reported_by': 'Site observer', 'text': TEXT, 'case_id': case['id'], 'place': 'north gate'}).json()
    return case, report


def analysis_with_proposals(evidence):
    """What the provider would return: findings with quotes, and typed proposals that name the finding behind them."""
    return work.Analysis(
        title='Two people at the gate',
        summary='One report describes two people meeting at the north gate.',
        findings=[work.Finding(claim='Two named people met at the north gate.',
                               citations=[work.Citation(source_id=evidence[0]['id'], quote='Marcus Vane met Dana Ortiz at the north gate at 21:40')],
                               uncertainty='One report, uncorroborated.')],
        gaps=['No second source.'],
        proposed_tasks=['Pull the gate camera for 21:30-22:00.'],
        proposed_graph=[
            work.GraphProposal(finding_index=0, kind='entity', entity_type='organization', name='Dockside Logistics'),   # new to the case
            work.GraphProposal(finding_index=0, kind='entity', entity_type='person', name='Marcus Vane'),                # the extraction already found this one
            work.GraphProposal(finding_index=0, kind='relationship', from_name='Marcus Vane', to_name='Dana Ortiz', link_type='associate'),
            work.GraphProposal(finding_index=0, kind='event', name='Two people met at the north gate.'),
            work.GraphProposal(finding_index=0, kind='relationship', from_name='Nobody Here', to_name='Marcus Vane', link_type='associate'),
        ])


async def fake_model(instruction, evidence):
    return analysis_with_proposals(evidence), {'provider': 'test', 'model': 'fixture', 'metrics': {}}


def reviewed_run(c, case, monkeypatch):
    monkeypatch.setattr(work, 'model_analysis', fake_model)
    c.post('/v1/work/assignments', headers=AN, json={'section': 'S2', 'case_id': case['id'], 'instruction': 'Read the reporting and propose what it supports'})
    asyncio.run(work.worker_tick())
    run = c.get('/v1/work', headers=AN).json()['runs'][0]
    c.patch(f"/v1/work/runs/{run['id']}", headers=AN, json={'revision': run['revision'], 'action': 'review'})
    return c.get('/v1/work', headers=AN).json()['runs'][0]


def test_typed_proposals_enter_the_case_graph_only_through_a_human_and_always_cited(monkeypatch):
    with TestClient(standalone_app()) as c:
        case, report = case_with_report(c)
        run = reviewed_run(c, case, monkeypatch)
        assert len(run['result']['proposed_graph']) == 5
        # a new node lands as suggested; one the extraction already found gains the analysis's citation instead
        new = c.post(f"/v1/work/runs/{run['id']}/graph", headers=AN, json={'index': 0})
        assert new.status_code == 201, new.text
        assert new.json()['status'] == 'suggested' and new.json()['existing'] is False
        known = c.post(f"/v1/work/runs/{run['id']}/graph", headers=AN, json={'index': 1})
        assert known.status_code == 201 and known.json()['existing'] is True
        link = c.post(f"/v1/work/runs/{run['id']}/graph", headers=AN, json={'index': 2})
        assert link.status_code == 201 and link.json()['kind'] == 'relationship'
        ev = c.post(f"/v1/work/runs/{run['id']}/graph", headers=AN, json={'index': 3})
        assert ev.status_code == 201 and ev.json()['kind'] == 'event'
        g = c.get(f"/v1/s2/cases/{case['id']}", headers=AN).json()['graph']
        applied = [e for e in g['entities'] if any(v['source'].startswith('analysis:') for v in e['evidence'])]
        assert {e['name'] for e in applied} == {'Dockside Logistics', 'Marcus Vane'}
        assert {e['status'] for e in applied} == {'suggested'}, "Decision P holds: the analyst still confirms"
        # the row carries the finding's own quote and the grade of the report it was quoted from
        cited = applied[0]['evidence'][-1]
        assert cited['quote'].startswith('Marcus Vane met Dana Ortiz') and cited['report_id'] == report['id'] and cited['reliability'] == 'A'
        # the event is dated and placed by the report it cites, not by the run
        analysis_event = next(v for v in g['events'] if v['type'] == 'analysis')
        assert analysis_event['at'] == report['at'] and analysis_event['place'] == 'north gate'
        # applying the same entity twice adds evidence rather than a second node
        again = c.post(f"/v1/work/runs/{run['id']}/graph", headers=AN, json={'index': 0})
        assert again.status_code == 201 and again.json()['existing'] is True
        assert len([e for e in c.get(f"/v1/s2/cases/{case['id']}", headers=AN).json()['graph']['entities'] if e['name'] == 'Dockside Logistics']) == 1


def test_a_proposal_cannot_be_applied_before_review_or_beyond_what_it_cites(monkeypatch):
    monkeypatch.setattr(work, 'model_analysis', fake_model)
    with TestClient(standalone_app()) as c:
        case, _ = case_with_report(c, 'Unreviewed')
        c.post('/v1/work/assignments', headers=AN, json={'section': 'S2', 'case_id': case['id'], 'instruction': 'Read the reporting and propose what it supports'})
        asyncio.run(work.worker_tick())
        run = c.get('/v1/work', headers=AN).json()['runs'][0]
        assert c.post(f"/v1/work/runs/{run['id']}/graph", headers=AN, json={'index': 0}).status_code == 409  # draft, not reviewed
        c.patch(f"/v1/work/runs/{run['id']}", headers=AN, json={'revision': run['revision'], 'action': 'review'})
        assert c.post(f"/v1/work/runs/{run['id']}/graph", headers=AN, json={'index': 9}).status_code == 422
        # a link to an entity nobody has proposed yet is refused rather than inventing the ends
        assert c.post(f"/v1/work/runs/{run['id']}/graph", headers=AN, json={'index': 4}).status_code == 422


def test_a_repeat_finding_is_marked_not_counted_as_a_second_source(monkeypatch):
    async def unique_claim(instruction, evidence):
        return work.Analysis(title='Gate closure', summary='One report.',
                             findings=[work.Finding(claim='A single observer described the gate at 21:40 and nobody else did.',
                                                    citations=[work.Citation(source_id=evidence[0]['id'], quote='left in a grey sedan')],
                                                    uncertainty='Uncorroborated.')],
                             gaps=[], proposed_tasks=[]), {'provider': 'test', 'model': 'fixture', 'metrics': {}}
    monkeypatch.setattr(work, 'model_analysis', unique_claim)
    with TestClient(standalone_app()) as c:
        case, _ = case_with_report(c, 'First pass')
        c.post('/v1/work/assignments', headers=AN, json={'section': 'S2', 'case_id': case['id'], 'instruction': 'Read the reporting once'})
        asyncio.run(work.worker_tick())
        first = c.get('/v1/work', headers=AN).json()['runs'][0]
        assert first['metrics'].get('repeats') == []   # nothing said it before
        c.post('/v1/work/assignments', headers=AN, json={'section': 'S2', 'case_id': case['id'], 'instruction': 'Read the same reporting again'})
        asyncio.run(work.worker_tick())
        runs = c.get('/v1/work', headers=AN).json()['runs']
        second = next(r for r in runs if r['id'] != first['id'])
        assert second['metrics']['repeats'] and second['metrics']['repeats'][0]['run_id'] == first['id']
        assert second['metrics']['repeats'][0]['basis']


def test_an_assignment_can_be_scoped_to_a_requirement_and_reads_only_what_is_inside_it(monkeypatch):
    seen = {}
    async def capture(instruction, evidence):
        seen['evidence'] = evidence
        return await fake_model(instruction, evidence)
    monkeypatch.setattr(work, 'model_analysis', capture)
    with TestClient(standalone_app()) as c:
        req = c.post('/v1/s2/requirements', headers=AN, json={'place': 'North gate approach', 'lat': 37.7897, 'lon': -122.3989, 'radius_km': 2,
                                                                       'question': 'What is happening at the north gate approach?', 'purpose': 'gate security'}).json()
        c.post('/v1/s2/reports', headers=AN, json={'reported_by': 'Site observer', 'text': 'Two people photographed the north gate.', 'lat': 37.7897, 'lon': -122.3989, 'place': 'north gate'})
        c.post('/v1/s2/reports', headers=AN, json={'reported_by': 'Far observer', 'text': 'Nothing at all in Lisbon tonight.', 'lat': 38.7223, 'lon': -9.1393, 'place': 'Lisbon'})
        bad = c.post('/v1/work/assignments', headers=AN, json={'section': 'S2', 'subject_type': 'requirement', 'subject_id': 'req_nope', 'instruction': 'Assess this requirement'})
        assert bad.status_code == 404
        half = c.post('/v1/work/assignments', headers=AN, json={'section': 'S2', 'subject_type': 'requirement', 'instruction': 'Assess this requirement'})
        assert half.status_code == 422
        a = c.post('/v1/work/assignments', headers=AN, json={'section': 'S2', 'subject_type': 'requirement', 'subject_id': req['id'], 'instruction': 'Assess what is inside this NAI'})
        assert a.status_code == 201 and a.json()['subject_type'] == 'requirement'
        asyncio.run(work.worker_tick())
        texts = " ".join(e['text'] for e in seen['evidence'])
        assert 'photographed the north gate' in texts, "reporting inside the radius is in scope"
        assert 'Lisbon' not in texts, "reporting outside the radius is not"
        assert any(e['id'].startswith('requirement:') for e in seen['evidence']), "the question itself is evidence"


def test_a_report_is_matched_to_the_case_it_belongs_to_with_the_reason_shown():
    with TestClient(standalone_app()) as c:
        case, _ = case_with_report(c, 'North gate loiterer')
        c.post(f"/v1/s2/cases/{case['id']}/decide", headers=AN, json={'kind': 'entity', 'id': [e['id'] for e in c.get(f"/v1/s2/cases/{case['id']}", headers=AN).json()['graph']['entities'] if e['name'] == 'Marcus Vane'][0], 'decision': 'confirm'})
        loose = c.post('/v1/s2/reports', headers=AN, json={'reported_by': 'Site observer', 'text': 'Marcus Vane came back to the dock tonight.', 'place': 'north gate'}).json()
        m = c.get(f"/v1/s2/reports/{loose['id']}/case-matches", headers=AN)
        assert m.status_code == 200, m.text
        d = m.json()
        assert d['attached_to'] is None
        hit = next(x for x in d['matches'] if x['case_id'] == case['id'])
        kinds = {r['kind'] for r in hit['reasons']}
        assert 'names' in kinds and 'reporter' in kinds
        assert any('Marcus Vane' in r['detail'] for r in hit['reasons'])
        # matching proposes; attaching is still the analyst's act, and the report keeps its provenance afterwards
        assert c.post(f"/v1/s2/reports/{loose['id']}/attach", headers=AN, json={'case_id': case['id']}).status_code == 200
        assert c.get(f"/v1/s2/reports/{loose['id']}/case-matches", headers=AN).json()['attached_to'] == case['id']
