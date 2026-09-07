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
