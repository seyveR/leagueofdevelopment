from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models import Child,Club
from .conftest import register,csrf
from .test_api import create_child,start,finish,admin_client

def test_completed_reports_snapshots_answers_pagination_and_access(client):
    register(client);child=create_child(client);session=start(client,child);finish(client,session,wrong=True)
    other=TestClient(app);register(other,'second@example.com');child2=create_child(other);session2=start(other,child2);finish(other,session2)
    with SessionLocal() as db:db.get(Child,child['id']).name='Изменённое имя';db.commit()
    admin=admin_client()
    page=admin.get('/api/admin/completions?limit=1').json()
    assert page['total']==2 and len(page['items'])==1
    second=admin.get('/api/admin/completions?limit=1&offset=1').json()
    assert second['items'][0]['session']['id']!=page['items'][0]['session']['id']
    assert admin.get('/api/admin/completions?offset=100').json()['items']==[]
    detail=admin.get(f"/api/admin/completions/{session['id']}")
    assert detail.status_code==200
    data=detail.json()
    assert data['parent']['email']=='parent@example.com' and data['session']['child_snapshot']['name']==child['name']
    assert data['result']['scores']['correct']==11
    assert len(data['answers'])==12 and data['answers'][0]['is_correct'] is False
    assert all(a['selected'] and a['correct'] and a['answered_at'] for a in data['answers'])
    assert data['task_set_version'] and data['result']['algorithm_version']
    assert 'password_hash' not in detail.text and 'token_hash' not in detail.text
    pending=start(client,child)
    assert admin.get(f"/api/admin/completions/{pending['id']}").status_code==404
    assert admin.get('/api/admin/completions/missing').status_code==404
    for path in ['/api/admin/completions',f"/api/admin/completions/{session['id']}",'/api/admin/club-transitions']:
        assert client.get(path).status_code==403
        assert TestClient(app).get(path).status_code==401
    for query in ['limit=0','limit=101','offset=-1']:
        assert admin.get('/api/admin/completions?'+query).status_code==422
        assert admin.get('/api/admin/club-transitions?'+query).status_code==422

def test_transition_groups_archive_and_duplicate_events(client):
    admin=admin_client()
    assert admin.get('/api/admin/completions').json()['items']==[]
    assert admin.get('/api/admin/club-transitions').json()['total_openings']==0
    register(client);child=create_child(client);session=start(client,child);finish(client,session)
    clubs=client.get(f"/api/sessions/{session['id']}/recommendations").json()
    first,second=clubs[0]['club'],clubs[1]['club']
    client.get('/api/clubs');client.get('/api/clubs/'+first['id'])
    assert admin.get('/api/admin/club-transitions').json()['total_openings']==0
    for club in [first,first,second]:
        body={'club_id':club['id'],'request_id':str(uuid4())}
        for _ in range(2):assert client.post(f"/api/sessions/{session['id']}/club-open",json=body).status_code==200
    with SessionLocal() as db:db.get(Club,first['id']).archived=True;db.commit()
    response=admin.get('/api/admin/club-transitions?limit=1').json()
    assert response['total']==2 and response['total_openings']==3
    assert response['items'][0]['club_id']==first['id'] and response['items'][0]['count']==2
    assert response['items'][0]['archived'] is True and response['items'][0]['last_opened_at']
    assert admin.get('/api/admin/club-transitions?limit=1&offset=1').json()['items'][0]['count']==1
    assert admin.get('/api/admin/stats').json()=={'completed':1,'club_open':3}
