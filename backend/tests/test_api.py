from uuid import uuid4
import json
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from app.main import app,CONSENT_VERSION
from app.db import SessionLocal
from app.models import User,Child,Answer,Result,Event,TaskSet,Rule,Club,Feedback,AuthSession
from app.security import hasher
from app.content import TASKS,SET_ID
from app.seed import seed
from .conftest import register,csrf

def create_child(c,age=8,city='Архангельск'):
    response=c.post('/api/children',json={'name':'Лисёнок','age':age,'gender':'unspecified','interests':['Творчество'],'city':city,'consent':True,'consent_version':CONSENT_VERSION})
    assert response.status_code==200,response.text
    return response.json()
def start(c,child):
    r=c.post('/api/sessions',json={'child_id':child['id'],'request_id':str(uuid4())});assert r.status_code==200,r.text;return r.json()
def finish(c,s,wrong=False):
    for i,t in enumerate(TASKS):
        if t['category']=='memory':assert c.post(f"/api/sessions/{s['id']}/hide",json={'task_id':t['id']}).status_code==200
        r=c.post(f"/api/sessions/{s['id']}/answers",json={'task_id':t['id'],'option_id':'o0' if wrong and i==0 else t['correct']});assert r.status_code==200,r.text
    r=c.post(f"/api/sessions/{s['id']}/complete");assert r.status_code==200,r.text;return r.json()
def admin_client():
    import secrets
    password=secrets.token_urlsafe(24)
    with SessionLocal() as db:db.add(User(email='admin@example.com',password_hash=hasher.hash(password),role='admin'));db.commit()
    c=TestClient(app);csrf(c);r=c.post('/api/auth/login',json={'email':'admin@example.com','password':password});assert r.status_code==200;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def test_registration_session_logout_and_hash(client):
    u=register(client)
    assert client.get('/api/auth/session').json()['user']['id']==u['id']
    with SessionLocal() as db:
        stored=db.get(User,u['id']);assert stored.password_hash.startswith('$argon2id$');assert 'test-password' not in stored.password_hash
    headers=client.post('/api/auth/login',json={'email':u['email'],'password':'test-password-123'}).headers.get_list('set-cookie')
    assert any('HttpOnly' in s and 'SameSite=strict' in s and 'liga_session' in s for s in headers)
    csrf(client);assert client.post('/api/auth/logout').status_code==200
    assert client.get('/api/state').status_code==401
    assert client.get('/api/auth/session').json()['user'] is None

def test_csrf_role_escalation_and_login_throttle(client):
    assert client.post('/api/auth/register',json={'email':'x@example.com','password':'test-password-123'}).status_code==403
    csrf(client)
    assert client.post('/api/auth/register',json={'email':'x@example.com','password':'test-password-123','role':'admin'}).status_code==422
    assert client.post('/api/auth/register',headers={'Origin':'https://evil.example'},json={'email':'x@example.com','password':'test-password-123'}).status_code==403
    for _ in range(14):assert client.post('/api/auth/login',json={'email':'missing@example.com','password':'test-password-123'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'missing@example.com','password':'test-password-123'}).status_code==429

def test_consent_profile_and_age_restriction(client):
    register(client)
    assert client.post('/api/children',json={'name':'Ребёнок','age':8,'gender':'male','city':'Архангельск'}).status_code==422
    c=create_child(client,6);assert c['consent_at'] and c['consent_version']==CONSENT_VERSION
    assert client.post('/api/sessions',json={'child_id':c['id'],'request_id':str(uuid4())}).status_code==422
    assert client.put('/api/children/'+c['id'],json={'name':'Новое имя','age':8,'gender':'female','city':'Архангельск','interests':[]}).status_code==200

def test_ownership_and_admin_permissions(client):
    register(client);c=create_child(client);s=start(client,c);finish(client,s)
    stranger=TestClient(app);register(stranger,'other@example.com')
    for path in [f"/api/children/{c['id']}",f"/api/sessions/{s['id']}",f"/api/sessions/{s['id']}/result",f"/api/sessions/{s['id']}/recommendations"]:assert stranger.get(path).status_code==404
    for suffix,payload in [('answers',{'task_id':'t01','option_id':'o0'}),('hide',{'task_id':'t07'}),('complete',None),('club-open',{'club_id':str(uuid4()),'request_id':str(uuid4())})]:assert stranger.post(f"/api/sessions/{s['id']}/{suffix}",json=payload).status_code==404
    assert stranger.post('/api/sessions',json={'child_id':c['id'],'request_id':str(uuid4())}).status_code==404
    assert stranger.put('/api/children/'+c['id'],json={'name':'X','age':8,'gender':'male','city':'X'}).status_code==404
    for path in ['/api/admin/clubs','/api/admin/rules','/api/admin/stats','/api/admin/feedback']:assert client.get(path).status_code==403
    assert client.post('/api/admin/clubs',json={}).status_code==403
    assert client.put('/api/admin/clubs/x',json={}).status_code==403
    assert client.put('/api/admin/clubs/x/rule',json={}).status_code==403

def test_answers_restoration_keys_memory_and_result(client):
    register(client);c=create_child(client);s=start(client,c);url=f"/api/sessions/{s['id']}"
    assert client.post(url+'/complete').status_code==409
    for i,t in enumerate(TASKS):
        detail=client.get(url).json()
        assert detail['session']['position']==i
        assert 'correct' not in json.dumps(detail) and 'algorithm_version' in detail['session']
        if t['category']=='memory':
            assert detail['task']['stimulus'] and not detail['task']['options']
            assert client.post(url+'/answers',json={'task_id':t['id'],'option_id':'o0'}).status_code==409
            assert client.post(url+'/hide',json={'task_id':t['id']}).status_code==200
            hidden=client.get(url).json();assert hidden['task']['stimulus'] is None and len(hidden['task']['options'])==3
            assert client.post(url+'/hide',json={'task_id':t['id']}).status_code==200
        body={'task_id':t['id'],'option_id':t['correct']}
        assert client.post(url+'/answers',json={**body,'option_id':'invalid'}).status_code==422
        assert client.post(url+'/answers',json=body).status_code==200
        assert client.post(url+'/answers',json=body).status_code==200
    r=client.post(url+'/complete').json();assert r['scores']['correct']==12
    assert r['scores']['attention']['percent']==100 and r['scores']['memory']['percent']==100
    assert client.post(url+'/complete').json()['id']==r['id']
    assert client.post(url+'/answers',json={'task_id':'t01','option_id':'o1'}).status_code==409
    with SessionLocal() as db:assert db.scalar(select(func.count()).select_from(Answer))==12;assert db.scalar(select(func.count()).select_from(Event).where(Event.kind=='completed'))==1

def test_scoring_snapshots_versions_and_repeat_start(client):
    register(client);c=create_child(client);key=str(uuid4());body={'child_id':c['id'],'request_id':key}
    s=client.post('/api/sessions',json=body).json();assert client.post('/api/sessions',json=body).json()['id']==s['id']
    client.put('/api/children/'+c['id'],json={'name':'Изменено','age':9,'gender':'unspecified','city':'Другой город'})
    r=finish(client,s,wrong=True);assert r['scores']['attention']['correct']==5;assert r['scores']['attention']['percent']==83.3;assert r['scores']['correct']==11
    detail=client.get(f"/api/sessions/{s['id']}").json();assert detail['session']['child_snapshot']['age']==8
    assert client.post('/api/sessions',json=body).json()['id']==s['id']
    assert start(client,c)['id']!=s['id']

def test_recommendations_archives_rules_events_feedback(client):
    register(client);c=create_child(client);s=start(client,c);finish(client,s)
    url=f"/api/sessions/{s['id']}";recs=client.get(url+'/recommendations').json();assert 3<=len(recs)<=5
    assert all(r['club']['city']=='Архангельск' and r['club']['min_age']<=8<=r['club']['max_age'] for r in recs)
    assert recs==client.get(url+'/recommendations').json()
    event={'club_id':recs[0]['club']['id'],'request_id':str(uuid4())}
    assert client.post(url+'/club-open',json=event).status_code==200;assert client.post(url+'/club-open',json=event).status_code==200
    feedback={'rating':5,'message':'Проверка','request_id':str(uuid4())};f=client.post('/api/feedback',json=feedback).json();assert client.post('/api/feedback',json=feedback).json()['id']==f['id']
    admin=admin_client();assert admin.get('/api/admin/stats').json()=={'completed':1,'club_open':1};assert len(admin.get('/api/admin/feedback').json())==1
    club=recs[0]['club'];club['archived']=True;id=club.pop('id');assert admin.put('/api/admin/clubs/'+id,json=club).status_code==200
    assert all(r['club']['id']!=id for r in client.get(url+'/recommendations').json())
    assert client.get('/api/clubs/'+id).status_code==404
    assert admin.put('/api/admin/clubs/'+id+'/rule',json={'metric':'attention','minimum':80,'maximum':100,'priority':20,'explanation':'Работа с деталями.'}).status_code==200
    from .test_marketplace import upgrade
    upgrade(client)
    different=start(client,create_child(client,8,'Другой город'));finish(client,different);assert client.get(f"/api/sessions/{different['id']}/recommendations").json()==[]

def test_seed_repeatable_and_admin_create_edit(client):
    with SessionLocal() as db:
        seed(db);seed(db);assert db.scalar(select(func.count()).select_from(TaskSet))==5;assert db.scalar(select(func.count()).select_from(Club))==6
    c=admin_client();body={'name':'Новый кружок','description':'Описание','min_age':7,'max_age':9,'city':'Архангельск','address':'Адрес','phone':'+7 (000) 000-00-00','price':'1000 ₽','photo_url':''}
    r=c.post('/api/admin/clubs',json=body);assert r.status_code==200,r.text;club=r.json();assert c.put('/api/admin/clubs/'+club['id'],json={**body,'name':'Изменённый кружок'}).status_code==200
    assert c.put('/api/admin/clubs/'+club['id']+'/rule',json={'metric':'memory','minimum':90,'maximum':20,'explanation':'X'}).status_code==422

def test_concurrent_starts_and_answers_are_idempotent(client):
    register(client);child=create_child(client)
    def concurrent_start(_):
        with TestClient(app) as other:
            other.cookies.update(dict(client.cookies));other.headers['X-CSRF-Token']=client.headers['X-CSRF-Token']
            return start(other,child)['id']
    with ThreadPoolExecutor(max_workers=4) as executor:ids=list(executor.map(concurrent_start,range(4)))
    assert len(set(ids))==1
    def concurrent_answer(_):
        with TestClient(app) as other:
            other.cookies.update(dict(client.cookies));other.headers['X-CSRF-Token']=client.headers['X-CSRF-Token']
            return other.post(f'/api/sessions/{ids[0]}/answers',json={'task_id':'t01','option_id':'o2'}).status_code
    with ThreadPoolExecutor(max_workers=4) as executor:assert list(executor.map(concurrent_answer,range(4)))==[200]*4
    with SessionLocal() as db:assert db.scalar(select(func.count()).select_from(Answer))==1

def test_failed_commit_rolls_back_answer_and_position(client,monkeypatch):
    from sqlalchemy.orm import Session as DBSession
    from sqlalchemy.exc import OperationalError
    register(client);child=create_child(client);s=start(client,child)
    commit=DBSession.commit;failed=False
    def commit_once(db):
        nonlocal failed
        if not failed and any(isinstance(item,Answer) for item in db.new):
            failed=True;raise OperationalError('simulated failure',None,Exception('unavailable'))
        return commit(db)
    monkeypatch.setattr(DBSession,'commit',commit_once)
    url=f"/api/sessions/{s['id']}";body={'task_id':'t01','option_id':'o2'}
    assert client.post(url+'/answers',json=body).status_code==503
    detail=client.get(url).json();assert detail['session']['position']==0 and detail['answers']==[]
    assert client.post(url+'/answers',json=body).status_code==200

def test_validation_never_echoes_password(client):
    csrf(client)
    response=client.post('/api/auth/register',json={'email':'p@example.com','password':'secret'})
    assert response.status_code==422 and 'secret' not in response.text

def test_child_and_club_create_retries_use_stable_ids(client):
    register(client)
    body={'name':'Ребёнок','age':8,'gender':'male','city':'Архангельск','consent':True,'consent_version':CONSENT_VERSION,'request_id':str(uuid4())}
    a=client.post('/api/children',json=body);b=client.post('/api/children',json=body)
    assert a.status_code==b.status_code==200 and a.json()['id']==b.json()['id']
    admin=admin_client();club={'name':'Кружок','description':'Описание','min_age':7,'max_age':9,'city':'Архангельск','address':'Адрес','phone':'+70000000000','price':'1000','request_id':str(uuid4())}
    a=admin.post('/api/admin/clubs',json=club);b=admin.post('/api/admin/clubs',json=club)
    assert a.status_code==b.status_code==200 and a.json()['id']==b.json()['id']
