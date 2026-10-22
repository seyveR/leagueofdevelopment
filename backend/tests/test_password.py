import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,delete,func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.main import app
from app.db import SessionLocal
from app.models import User,AuthSession
from app.security import hasher,COOKIE
from .conftest import register,csrf

def login(client,email,password):
    csrf(client)
    response=client.post('/api/auth/login',json={'email':email,'password':password})
    if response.status_code==200:client.headers['X-CSRF-Token']=response.json()['csrf']
    return response

@pytest.mark.parametrize('role',['parent','admin'])
def test_change_own_password_revokes_all_sessions_and_keeps_other_users(client,role):
    password=secrets.token_urlsafe(24);new_password=secrets.token_urlsafe(24);email=f'{role}@example.com'
    with SessionLocal() as db:
        user=User(email=email,password_hash=hasher.hash(password),role=role);db.add(user);db.commit();user_id=user.id
    assert login(client,email,password).status_code==200
    second=TestClient(app);assert login(second,email,password).status_code==200
    other=TestClient(app);register(other,'unrelated@example.com')
    body={'current_password':password,'new_password':new_password,'confirmation':new_password}
    response=client.post('/api/auth/password',json=body)
    assert response.status_code==200
    assert password not in response.text and new_password not in response.text
    assert COOKIE not in client.cookies
    assert client.get('/api/auth/session').json()['user'] is None
    assert second.get('/api/admin/stats' if role=='admin' else '/api/state').status_code==401
    assert other.get('/api/state').status_code==200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AuthSession).where(AuthSession.user_id==user_id))==0
        assert db.get(User,user_id).role==role
        assert hasher.verify(db.get(User,user_id).password_hash,new_password)
    assert login(client,email,password).status_code==401
    assert login(client,email,new_password).status_code==200

def test_invalid_current_confirmation_length_and_csrf_keep_session(client):
    register(client);password='test-password-123';new='another-new-password'
    body={'current_password':password,'new_password':new,'confirmation':new}
    assert client.post('/api/auth/password',json={**body,'current_password':'wrong'}).status_code==400
    assert client.post('/api/auth/password',json={**body,'confirmation':'not-matching-password'}).status_code==422
    response=client.post('/api/auth/password',json={**body,'new_password':'short','confirmation':'short'})
    assert response.status_code==422 and 'short' not in response.text
    assert client.post('/api/auth/password',json=body,headers={'X-CSRF-Token':'wrong'}).status_code==403
    assert client.post('/api/auth/password',json={**body,'email':'other@example.com'}).status_code==422
    assert client.get('/api/state').status_code==200

def test_password_commit_failure_keeps_old_hash_and_sessions(client,monkeypatch):
    u=register(client);old='test-password-123';new='another-new-password'
    original=Session.commit
    commits=0
    def fail_password_commit(db):
        nonlocal commits
        commits+=1
        # First commit records throttling; the second commits the password and revocations.
        if commits==2:raise OperationalError('simulated failure',None,Exception('unavailable'))
        return original(db)
    monkeypatch.setattr(Session,'commit',fail_password_commit)
    response=client.post('/api/auth/password',json={'current_password':old,'new_password':new,'confirmation':new})
    assert response.status_code==503
    assert client.get('/api/state').status_code==200
    with SessionLocal() as db:
        assert hasher.verify(db.get(User,u['id']).password_hash,old)
        assert db.scalar(select(func.count()).select_from(AuthSession).where(AuthSession.user_id==u['id']))==1

def test_logout_after_external_revocation_is_idempotent(client):
    u=register(client)
    with SessionLocal() as db:db.execute(delete(AuthSession).where(AuthSession.user_id==u['id']));db.commit()
    assert client.get('/api/state').status_code==401
    response=client.post('/api/auth/logout')
    assert response.status_code==200 and COOKIE not in client.cookies
    csrf(client);assert client.post('/api/auth/logout').status_code==200
