from fastapi.testclient import TestClient
from coptoc.app import app

BC = {'X-TOC-Role': 'battle_captain'}
AN = {'X-TOC-Role': 'analyst'}


def test_manual_person_entry_and_duty_update():
    with TestClient(app) as c:
        snap = c.get('/v1/cop/snapshot').json()
        payload = {'name': 'Workspace test person', 'role': 'Coordinator', 'team_id': snap['teams'][0]['id'], 'email': 'workspace-fixture@example.test'}
        assert c.post('/v1/cop/people', headers=AN, json=payload).status_code == 403
        response = c.post('/v1/cop/people', headers=BC, json=payload)
        assert response.status_code == 201, response.text
        pid = response.json()['id']
        assert c.post('/v1/cop/people', headers=BC, json=payload).status_code == 409
        assignment = {'on_shift': True, 'shift_role': 'Coordinator'}
        assert c.patch(f'/v1/cop/people/{pid}/assignment', headers=AN, json=assignment).status_code == 403
        assert c.patch(f'/v1/cop/people/{pid}/assignment', headers=BC, json=assignment).status_code == 200
        person = next(p for p in c.get('/v1/cop/snapshot').json()['people'] if p['id'] == pid)
        assert person['on_shift'] and person['shift_role'] == 'Coordinator'


def test_activity_pages_preserve_case_access_and_separate_read_audits():
    with TestClient(app) as c:
        case = c.post('/v1/s2/cases', headers=BC, json={'title': 'Private activity test case', 'kind': 'person'}).json()
        assert c.get('/v1/s2/cases/' + case['id'], headers=BC).status_code == 200
        bc_log = c.get('/v1/cop/activity?include_reads=true', headers=BC).json()
        assert any(x['type'] == 's2.case.read' and x['subject'] == case['id'] for x in bc_log['items'])
        public_log = c.get('/v1/cop/activity?include_reads=true', headers={'X-TOC-Role': 'ep'}).json()
        assert not any(x['subject'] == case['id'] for x in public_log['items'])
        assert not any(x['summary'].find('Private activity test case') >= 0 for x in c.get('/v1/cop/snapshot', headers={'X-TOC-Role': 'ep'}).json()['log'])
        ordinary = c.get('/v1/cop/activity', headers=BC).json()['items']
        assert not any(x['type'].endswith('.read') for x in ordinary)
        page = c.get('/v1/cop/activity?limit=1&include_reads=true', headers=BC).json()
        assert page['next_cursor'] is not None
        earlier = c.get('/v1/cop/activity', headers=BC, params={'limit':1,'include_reads':True,'before':page['next_cursor']}).json()
        assert earlier['items'][0]['id'] != page['items'][0]['id']
