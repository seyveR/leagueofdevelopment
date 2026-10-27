from datetime import timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.models import now
from .conftest import register
from .test_api import admin_client
from .test_marketplace import upgrade

def test_favorites_and_catalog_filters_are_personal(client):
    register(client);clubs=client.get('/api/market/programs?age=8&city=Архангельск').json();assert len(clubs)==6
    id=clubs[0]['id']
    for _ in range(2):assert client.put('/api/favorites/'+id).status_code==200
    assert client.get('/api/favorites').json()==[id]
    other=TestClient(app);register(other,'favorite-other@example.com');assert other.get('/api/favorites').json()==[]
    assert client.get('/api/market/programs?max_price=0').json()==[]
    assert client.get('/api/market/programs?age=99').status_code==422
    assert client.get('/api/market/programs?format=unknown').status_code==422
    assert client.delete('/api/favorites/'+id).status_code==200
    assert client.get('/api/favorites').json()==[]

def test_consultation_entitlement_slot_collision_and_cancel(client):
    register(client);admin=admin_client();time=(now()+timedelta(days=3)).isoformat()
    response=admin.post('/api/admin/specialists',json={'name':'Тестовый специалист','description':'Тестовая консультация, не реальная услуга','contact':'Не для реального обращения','slots':[time],'is_test':True})
    assert response.status_code==200,response.text;id=response.json()['id']
    body={'specialist_id':id,'starts_at':time,'contact':'parent@example.com','request_id':str(uuid4())}
    assert client.post('/api/consultations',json=body).status_code==402
    upgrade(client);first=client.post('/api/consultations',json=body);assert first.status_code==200,first.text
    assert client.post('/api/consultations',json=body).json()['id']==first.json()['id']
    other=TestClient(app);register(other,'consult-other@example.com');upgrade(other)
    assert other.post('/api/consultations',json={**body,'request_id':str(uuid4())}).status_code==409
    assert other.post('/api/consultations/'+first.json()['id']+'/cancel').status_code==404
    assert client.post('/api/consultations/'+first.json()['id']+'/cancel').status_code==200
    assert other.post('/api/consultations',json={**body,'request_id':str(uuid4())}).status_code==200
