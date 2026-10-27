from sqlalchemy import select
from app.db import SessionLocal
from app.models import User,Result
from app.platform_models import Notification
from app.platform_services import notify
from .conftest import register
from .test_api import create_child,start,finish,admin_client

def test_weighted_rules_explanations_and_sensitive_access(client):
    register(client);child=create_child(client);session=start(client,child);finish(client,session);admin=admin_client()
    url='/api/market/recommendations/'+session['id']
    response=client.get(url);assert response.status_code==200 and 1<=len(response.json())<=5
    assert all(r['explanation'] and r['rules_version']=='weighted-1.0.0' for r in response.json())
    weights=admin.get('/api/admin/recommendation-weights').json();assert weights['interests']==30
    assert client.put('/api/admin/recommendation-weights',json=weights).status_code==403
    assert admin.put('/api/admin/recommendation-weights',json={**weights,'interests':101}).status_code==422
    assert admin.put('/api/admin/recommendation-weights',json={**weights,'interests':90}).status_code==200
    assert client.get(url+'?max_price=0').json()==[]
    assert client.get(url+'?format=online').json()==[]

def test_notification_delivery_respects_settings_and_deduplicates(client):
    user=register(client);settings=client.get('/api/settings').json()['settings']
    assert client.put('/api/settings',json={**settings,'notify_bookings':False}).status_code==200
    with SessionLocal() as db:
        notify(db,user['id'],'booking','Заявка','key-one');db.commit()
        assert not db.scalar(select(Notification).where(Notification.user_id==user['id']))
    assert client.put('/api/settings',json=settings).status_code==200
    with SessionLocal() as db:
        notify(db,user['id'],'booking','Заявка','key-one');notify(db,user['id'],'booking','Заявка','key-one');db.commit()
    notices=client.get('/api/notifications').json();assert len(notices)==1
    assert client.post('/api/notifications/'+notices[0]['id']+'/read').status_code==200
