import pytest
from uuid import uuid4
from app.db import SessionLocal
from app.models import TestSession as TestRun,TaskSet
from .conftest import register
from .test_api import create_child

@pytest.mark.parametrize('age',[4,6,11,15])
def test_all_age_scenarios_resume_adaptation_and_protected_keys(client,age):
    register(client);child=create_child(client,age)
    response=client.post('/api/sessions',json={'child_id':child['id'],'request_id':str(uuid4()),'scenario':'age-v2'})
    assert response.status_code==200,response.text
    session=response.json();id=session['id'];categories=set();mechanics=set();levels=[]
    for n in range(12):
        detail=client.get('/api/sessions/'+id).json();task=detail['task'];assert detail['total']==12
        assert 'correct' not in task and 'advanced' not in task and 'task_trace' not in detail['session']
        categories.add(task['category']);mechanics.add(task['mechanic']);levels.append(task['difficulty'])
        if task['category']=='memory':
            assert task['stimulus'] and task['options']==[]
            assert client.post(f'/api/sessions/{id}/hide',json={'task_id':task['id']}).status_code==200
            assert client.get('/api/sessions/'+id).json()['task']['stimulus'] is None
        with SessionLocal() as db:correct=db.get(TestRun,id).task_trace[n]['task']['correct']
        result=client.post(f'/api/sessions/{id}/answers',json={'task_id':task['id'],'option_id':correct})
        assert result.status_code==200,result.text
    assert len(categories)==6 and {'search','memory','sequence','match','target'}.issubset(mechanics)
    assert levels[0]==1 and 2 in levels
    result=client.post(f'/api/sessions/{id}/complete').json()
    assert result['scores']['correct']==12 and result['algorithm_version']=='familiarisation-2.0.0'
    for category in categories:assert result['scores'][category]['total']==2
    with SessionLocal() as db:
        stored=db.get(TestRun,id)
        assert len(stored.task_trace)==12 and stored.conditions['voice']=='ru-sofia'
        assert all(t['rules_version']=='adaptive-1.0.0' for t in stored.task_trace)
