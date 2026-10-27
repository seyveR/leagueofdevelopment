from datetime import timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app,CONSENT_VERSION
from app.db import SessionLocal
from app.models import now,User
from app.platform_models import Subscription,Booking,Notification
from .conftest import csrf,register
from .test_api import create_child,admin_client,start,finish

def partner(email='partner@example.com'):
    c=TestClient(app);csrf(c)
    response=c.post('/api/partner/register',json={'email':email,'password':'partner-password-123','consent':True,'organization':{'name':'Организация','city':'Архангельск','contact':'partner@example.com','description':'Занятия'}})
    assert response.status_code==200,response.text;c.headers['X-CSRF-Token']=response.json()['csrf'];return c
def published(partner,admin):
    org=partner.get('/api/partner/organization').json()
    assert partner.put('/api/partner/organization',json={k:org[k] for k in ['name','description','city','contact','document_id']}).status_code==200
    assert admin.post(f"/api/admin/organizations/{org['id']}/decision",json={'approved':True}).status_code==200
    body={'name':'Рисование студия','description':'Занятия цветом','min_age':3,'max_age':17,'city':'Архангельск','address':'Адрес','phone':'+7 (000) 000-00-00','price':'1500 ₽','price_rub':1500,'format':'offline','tags':['Творчество'],'schedule':'Вторник 18:00','request_id':str(uuid4())}
    response=partner.post('/api/partner/programs',json=body);assert response.status_code==200,response.text
    program=response.json()
    assert admin.post(f"/api/admin/programs/{program['id']}/decision",json={'approved':True}).status_code==200
    slot=partner.post(f"/api/partner/programs/{program['id']}/slots",json={'starts_at':(now()+timedelta(days=2)).isoformat(),'capacity':1}).json()
    return program,slot
def upgrade(c):
    order=c.post('/api/payments/orders',json={'plan_id':'premium','request_id':str(uuid4())});assert order.status_code==200,order.text
    assert c.post('/api/payments/orders/'+order.json()['id']+'/simulate-confirm').status_code==200

def test_booking_closed_loop_permissions_capacity_and_notifications(client):
    p=partner();admin=admin_client();program,slot=published(p,admin);stranger=partner('stranger@example.com')
    assert stranger.get('/api/partner/programs').json()==[]
    assert stranger.put('/api/partner/programs/'+program['id'],json={}).status_code in [404,422]
    register(client);child=create_child(client)
    body={'child_id':child['id'],'slot_id':slot['id'],'contact':'parent@example.com','consent':True,'request_id':str(uuid4())}
    response=client.post('/api/bookings',json=body);assert response.status_code==200,response.text;b=response.json()
    assert client.post('/api/bookings',json=body).json()['id']==b['id']
    assert len(p.get('/api/partner/bookings').json())==1
    assert stranger.post('/api/bookings/'+b['id']+'/status',json={'status':'accepted'}).status_code==404
    second=TestClient(app);register(second,'second-booking@example.com');other=create_child(second)
    assert second.post('/api/bookings',json={**body,'child_id':other['id'],'request_id':str(uuid4())}).status_code==409
    assert client.post('/api/bookings/'+b['id']+'/status',json={'status':'completed'}).status_code==409
    for status in ['accepted','completed']:
        r=p.post('/api/bookings/'+b['id']+'/status',json={'status':status,'note':'Связались'});assert r.status_code==200,r.text
    assert client.post('/api/bookings/'+b['id']+'/status',json={'status':'cancellation_requested','note':'Больше не посещаем'}).status_code==200
    assert p.post('/api/bookings/'+b['id']+'/status',json={'status':'ended'}).status_code==200
    assert len(client.get('/api/bookings').json()[0]['history'])==5
    assert len(client.get('/api/notifications').json())>=3
    csv=p.get('/api/partner/bookings.csv');assert csv.status_code==200 and b['id'] in csv.text
    assert b['id'] not in stranger.get('/api/partner/bookings.csv').text

def test_tariff_server_limits_idempotent_simulation_and_existing_children(client):
    register(client);create_child(client)
    payload={'name':'Второй','age':8,'gender':'male','interests':[],'city':'Архангельск','consent':True,'consent_version':CONSENT_VERSION}
    assert client.post('/api/children',json=payload).status_code==402
    order=client.post('/api/payments/orders',json={'plan_id':'premium','request_id':str(uuid4())}).json()
    url='/api/payments/orders/'+order['id']+'/simulate-confirm'
    first=client.post(url);assert first.status_code==200
    second=client.post(url);assert first.json()['expires_at']==second.json()['expires_at']
    assert client.post('/api/children',json=payload).status_code==200
    user_id=client.get('/api/auth/session').json()['user']['id']
    with SessionLocal() as db:db.get(Subscription,user_id).expires_at=now()-timedelta(days=1);db.commit()
    assert len(client.get('/api/state').json()['children'])==2
    assert client.post('/api/children',json=payload).status_code==402
    assert client.get('/api/plans').json()['entitlement']['status']=='free'

def test_review_moderation_only_published_rating(client):
    register(client);child=create_child(client);admin=admin_client()
    club=client.get('/api/market/programs').json()[0]
    url=f"/api/market/programs/{club['id']}/reviews"
    assert client.post(url,json={'rating':5,'message':'Занятия понравились'}).status_code==403
    finish(client,start(client,child))
    review=client.post(url,json={'rating':5,'message':'Занятия понравились'}).json()
    assert client.get('/api/market/programs/'+club['id']).json()['rating'] is None
    assert admin.post('/api/admin/reviews/'+review['id']+'/decision',json={'approved':True}).status_code==200
    assert client.get('/api/market/programs/'+club['id']).json()['rating']==5
    assert client.post(url,json={'rating':3,'message':'Дополнение к отзыву'}).status_code==200
    assert client.get('/api/market/programs/'+club['id']).json()['rating'] is None

def test_block_revokes_sessions_consent_and_account_deletion(client):
    user=register(client);child=create_child(client);finish(client,start(client,child));admin=admin_client()
    assert client.put('/api/account/consent',json={'consent':False}).status_code==200
    assert client.post('/api/sessions',json={'child_id':child['id'],'request_id':str(uuid4())}).status_code==403
    exported=client.get('/api/account/export');assert exported.status_code==200
    assert 'password_hash' not in exported.text and 'token_hash' not in exported.text
    assert admin.post('/api/admin/users/'+user['id']+'/block',json={'blocked':True}).status_code==200
    assert client.get('/api/state').status_code==401
    assert admin.post('/api/admin/users/'+user['id']+'/block',json={'blocked':False}).status_code==200
    csrf(client);r=client.post('/api/auth/login',json={'email':user['email'],'password':'test-password-123'});client.headers['X-CSRF-Token']=r.json()['csrf']
    assert client.post('/api/account/delete',json={'password':'test-password-123','confirmation':'УДАЛИТЬ'}).status_code==200
    with SessionLocal() as db:assert db.get(User,user['id']) is None
