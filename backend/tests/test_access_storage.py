import struct,zlib,secrets
from datetime import timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models import now,User
from app.platform_models import AccessToken
from app.security import digest
from app.storage import FILES
from .conftest import register,csrf
from .test_marketplace import partner
from .test_api import admin_client

def png():
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\x00\x00'))+chunk(b'IEND',b'')

def test_files_types_limits_and_private_access(client,tmp_path,monkeypatch):
    monkeypatch.setattr(FILES,'root',tmp_path);p=partner();other=partner('other-files@example.com');admin=admin_client()
    assert p.post('/api/files',content=b'<script/>',headers={'Content-Type':'image/png'}).status_code==422
    photo=p.post('/api/files',content=png(),headers={'Content-Type':'image/png'});assert photo.status_code==200,photo.text
    assert TestClient(app).get(photo.json()['url']).headers['content-type']=='image/png'
    document=p.post('/api/files?purpose=document',content=b'%PDF-1.4\n%test\n%%EOF',headers={'Content-Type':'application/pdf'});assert document.status_code==200
    url=document.json()['url']
    assert TestClient(app).get(url).status_code==401
    assert other.get(url).status_code==404
    assert p.get(url).status_code==200 and admin.get(url).status_code==200
    assert p.post('/api/files',content=b'x'*(3*1024*1024+1)).status_code==413
    register(client);assert client.post('/api/files',content=png()).status_code==403

def test_one_time_recovery_and_verification_tokens(client):
    user=register(client);token=secrets.token_urlsafe(40);verification=secrets.token_urlsafe(40)
    with SessionLocal() as db:
        db.add(AccessToken(user_id=user['id'],kind='reset',token_hash=digest(token),expires_at=now()+timedelta(minutes=5)))
        db.add(AccessToken(user_id=user['id'],kind='verify',token_hash=digest(verification),expires_at=now()+timedelta(minutes=5)));db.commit()
    assert client.post('/api/auth/verify-email',json={'token':verification}).status_code==200
    assert client.post('/api/auth/verify-email',json={'token':verification}).status_code==400
    assert client.get('/api/account').json()['email_verified'] is True
    assert client.post('/api/auth/reset',json={'token':token,'password':'new-reset-password'}).status_code==200
    assert client.get('/api/state').status_code==401
    csrf(client)
    assert client.post('/api/auth/reset',json={'token':token,'password':'another-password'}).status_code==400
    assert client.post('/api/auth/login',json={'email':user['email'],'password':'test-password-123'}).status_code==401
    assert client.post('/api/auth/login',json={'email':user['email'],'password':'new-reset-password'}).status_code==200
