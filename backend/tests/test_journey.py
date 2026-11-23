from uuid import uuid4
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from app.main import app
from app.db import SessionLocal
from app.models import Answer,TaskSet
from app.platform_models import TrialSlot,Booking
from app.journey_content import SETS,group_for,VERSION
from app.journey_assessment import evaluate,validate
from app.seed import seed
from app.catalog_2026 import PROGRAMS,uid
from .conftest import register
from .test_api import create_child,admin_client

def payload(task):
    kind=task['mechanic'];cfg=task['config']
    if kind=='combine':return {'selected':['0','1']}
    if kind=='draw':return {'choice':'0','strokes':[[[0.1,0.1],[0.5,0.5]]]}
    if kind=='sort':return {'buckets':cfg['key']}
    if kind=='odd':return cfg['key']
    return {'selected':cfg['key']}

@pytest.mark.parametrize('age,expected',[(3,None),(4,(4,7)),(7,(4,7)),(8,(8,10)),(10,(8,10)),(11,(11,14)),(14,(11,14)),(15,(15,17)),(17,(15,17)),(18,None)])
def test_age_boundaries(age,expected):assert group_for(age)==expected

@pytest.mark.parametrize('age',[5,9,13,16])
def test_full_journey_resume_separate_raw_answers_and_history(client,age):
    register(client);child=create_child(client,age);group=group_for(age);spec=SETS[f'{group[0]}-{group[1]}']
    before=client.get('/api/journey',params={'child_id':child['id']}).json();assert before['count'] in (20,30,40,50)
    body={'child_id':child['id'],'request_id':str(uuid4())}
    from app.models import TestSession
    with SessionLocal() as db:
        db.add(TestSession(id=body['request_id'],child_id=child['id'],task_set_id=spec['id'],algorithm_version=VERSION,child_snapshot={'name':child['name'],'age':age,'city':child['city'],'interests':[]},conditions={'speech':False}));db.commit()
    session=client.get('/api/sessions/'+body['request_id']).json()['session'];id=session['id'];assert session['algorithm_version']==VERSION
    assert client.post('/api/sessions/'+id+'/complete').status_code==409
    for i,task in enumerate(spec['tasks']):
        detail=client.get('/api/journey/'+id).json();assert detail['session']['position']==i
        assert 'key' not in detail['task']['config'] and 'direction_key' not in detail['task']['config']
        if task['mechanic']=='memory':
            assert 'choices' not in detail['task']['config']
            assert client.post('/api/journey/'+id+'/answers',json={'task_id':task['id'],'payload':payload(task)}).status_code==409
            assert client.post('/api/sessions/'+id+'/hide',json={'task_id':task['id']}).status_code==200
            assert 'material' not in client.get('/api/journey/'+id).json()['task']['config']
        answer={'task_id':task['id'],'payload':payload(task)}
        saved=client.post('/api/journey/'+id+'/answers',json=answer);assert saved.status_code==200,saved.text
        assert client.post('/api/journey/'+id+'/answers',json=answer).json()['position']==i+1
    response=client.post('/api/sessions/'+id+'/complete');assert response.status_code==200,response.text
    scores=response.json()['scores'];assert scores['completed']==10 and all(scores[k]['percent']==100 for k in ['logic','memory','attention','spatial','story'])
    assert client.post('/api/sessions/'+id+'/complete').json()['id']==response.json()['id']
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Answer).where(Answer.session_id==id))==10
        assert all(a.payload and a.option_id=='interactive' for a in db.scalars(select(Answer).where(Answer.session_id==id)))
        assert db.get(TaskSet,spec['id']).tasks==spec['tasks']
    other=TestClient(app);register(other,f'other{age}@example.com')
    assert other.get('/api/journey/'+id).status_code==404
    assert other.post('/api/journey/'+id+'/answers',json=answer).status_code==404
    admin=admin_client();report=admin.get('/api/admin/completions/'+id);assert report.status_code==200,report.text
    assert len(report.json()['answers'])==10 and report.json()['answers'][0]['is_correct'] is None
    recommendations=client.get('/api/market/recommendations/'+id).json();assert recommendations
    assert all(r['club']['min_age']<=age<=r['club']['max_age'] and r['rules_version']=='discovery-match-1.0.0' for r in recommendations)
    assert client.post('/api/sessions/'+id+'/club-open',json={'club_id':recommendations[0]['club']['id'],'request_id':str(uuid4())}).status_code==200

def test_scores_change_with_actions_and_reject_bad_payloads():
    tasks=SETS['15-17']['tasks'];answers={t['id']:payload(t) for t in tasks}
    good=evaluate(tasks,answers)
    answers['d6']={'selected':['2','2','2']};answers['d8']={'selected':[]};answers['d7']={'selected':[]}
    changed=evaluate(tasks,answers)
    assert good['affinities']!=changed['affinities'] and good['attention']['percent']>changed['attention']['percent']
    from fastapi import HTTPException
    with pytest.raises(HTTPException):validate(tasks[0],{'selected':['999']})
    with pytest.raises(HTTPException):validate(tasks[1],{'choice':'0','strokes':[[[float('nan'),0]]]})
    with pytest.raises(HTTPException):validate(tasks[7],{'selected':['0','0']})

def test_catalog_import_slots_and_booking_no_duplicates(client):
    register(client);child=create_child(client,5)
    with SessionLocal() as db:
        before=db.scalar(select(func.count()).select_from(TrialSlot));seed(db)
        assert db.scalar(select(func.count()).select_from(TrialSlot))==before
    club=uid('program/running');detail=client.get('/api/market/programs/'+club);assert detail.status_code==200,detail.text
    slots=detail.json()['slots'];assert len(slots)>=2
    body={'child_id':child['id'],'slot_id':slots[0]['id'],'request_id':str(uuid4()),'contact':'parent@example.com','consent':True}
    response=client.post('/api/bookings',json=body);assert response.status_code==200,response.text
    assert client.post('/api/bookings',json=body).json()['id']==response.json()['id']
    assert client.post('/api/bookings',json={**body,'request_id':str(uuid4())}).json()['id']==response.json()['id']
    bookings=client.get('/api/bookings').json();assert len(bookings)==1
    assert bookings[0]['program_address']=='Ул. Гайдара, д. 63' and bookings[0]['program_phone']=='89118717647' and bookings[0]['program_city']=='Архангельск'
    assert len(PROGRAMS)==14
