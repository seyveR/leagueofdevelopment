from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.domain_content import SETS
from .conftest import register
from .test_api import create_child,admin_client

def test_five_independent_sets_resume_memory_and_creativity(client):
    register(client);child=create_child(client)
    catalog=client.get('/api/domain-tests',params={'child_id':child['id']}).json()
    assert len(catalog)==5 and len({t['set_id'] for t in catalog})==5
    sessions=[]
    for item in catalog:
        body={'child_id':child['id'],'request_id':str(uuid4())}
        response=client.post('/api/domain-tests/'+item['code']+'/start',json=body)
        assert response.status_code==200,response.text
        s=response.json();sessions.append(s['id'])
        assert client.post('/api/domain-tests/'+item['code']+'/start',json=body).json()['id']==s['id']
        tasks=SETS[('6-9',item['code'])]['tasks']
        for task in tasks:
            detail=client.get('/api/sessions/'+s['id']).json();assert detail['total']==6
            assert 'correct' not in detail['task']
            if item['code']=='memory':
                assert not detail['task']['options']
                assert client.post('/api/sessions/'+s['id']+'/hide',json={'task_id':task['id']}).status_code==200
                assert client.get('/api/sessions/'+s['id']).json()['task']['stimulus'] is None
            answer={'task_id':task['id'],'option_id':'o2' if item['code']=='imagination' else task['correct']}
            assert client.post('/api/sessions/'+s['id']+'/answers',json=answer).status_code==200
        result=client.post('/api/sessions/'+s['id']+'/complete');assert result.status_code==200,result.text
        scores=result.json()['scores'];assert scores['total']==6 and scores['completed']==6
        if item['code']=='imagination':assert not scores['scored'] and 'imagination' not in scores
        else:assert scores[item['code']]['percent']==100
    assert len(set(sessions))==5
    other=TestClient(app);register(other,'other-domain@example.com')
    assert other.get('/api/domain-tests',params={'child_id':child['id']}).status_code==404
    for id in sessions:assert other.get('/api/sessions/'+id).status_code==404
    admin=admin_client()
    assert admin.get('/api/admin/completions/'+sessions[-1]).json()['answers'][0]['is_correct'] is None

def test_parallel_sets_keep_progress_and_legacy_path(client):
    register(client);child=create_child(client)
    started=[client.post('/api/domain-tests/'+code+'/start',json={'child_id':child['id'],'request_id':str(uuid4())}).json() for code in ['attention','memory']]
    assert started[0]['id']!=started[1]['id']
    assert client.get('/api/sessions/'+started[0]['id']).json()['session']['position']==0
    legacy=client.post('/api/sessions',json={'child_id':child['id'],'request_id':str(uuid4())})
    assert legacy.status_code==200 and legacy.json()['algorithm_version']!='domains-1.0.0'
