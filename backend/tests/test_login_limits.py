from datetime import timedelta
from app.db import SessionLocal
from app.models import User,LoginBucket,now
from app import security
from .conftest import register,csrf

PASSWORD='test-password-123'

def login(client,email='parent@example.com',password=PASSWORD):
    response=client.post('/api/auth/login',json={'email':email,'password':password})
    if response.status_code==200:client.headers['X-CSRF-Token']=response.json()['csrf']
    return response

def test_frequent_valid_logins_and_account_switches_never_hit_old_limits(client):
    register(client)
    with SessionLocal() as db:
        db.add(User(email='admin@example.com',role='admin',password_hash=security.hasher.hash(PASSWORD)))
        # Old shared proxy/email limits must not lock out existing users after upgrade.
        for key in ['ip:testclient','email:parent@example.com','email:admin@example.com']:
            bucket=db.get(LoginBucket,security.digest(key))
            if bucket:bucket.attempts=100
            else:db.add(LoginBucket(id=security.digest(key),attempts=100,window_start=now()))
        db.commit()
    for index in range(32):
        assert client.post('/api/auth/logout').status_code==200
        csrf(client)
        response=login(client,'parent@example.com' if index%2==0 else 'admin@example.com')
        assert response.status_code==200,response.text

def test_fifteenth_failure_starts_one_minute_pause_without_extension(client,monkeypatch):
    csrf(client);clock=[now()];monkeypatch.setattr(security,'now',lambda:clock[0])
    for _ in range(14):assert login(client,'missing@example.com').status_code==401
    response=login(client,'missing@example.com')
    assert response.status_code==429 and response.headers['Retry-After']=='60'
    clock[0]+=timedelta(seconds=40)
    response=login(client,'missing@example.com')
    assert response.status_code==429 and response.headers['Retry-After']=='20'
    clock[0]+=timedelta(seconds=21)
    assert login(client,'missing@example.com').status_code==401
    with SessionLocal() as db:
        assert db.get(LoginBucket,security.login_failure_key('missing@example.com')).attempts==1

def test_correct_password_bypasses_pause_resets_failures_and_keeps_other_accounts_independent(client):
    register(client)
    for _ in range(14):assert login(client,password='wrong-password').status_code==401
    assert login(client,password='wrong-password').status_code==429
    assert login(client,'unrelated@example.com',password='wrong-password').status_code==401
    assert login(client).status_code==200
    with SessionLocal() as db:
        assert db.get(LoginBucket,security.login_failure_key('parent@example.com')).attempts==0
        assert db.get(LoginBucket,security.login_failure_key('unrelated@example.com')).attempts==1
    for _ in range(14):assert login(client,password='wrong-password').status_code==401
    assert login(client).status_code==200
