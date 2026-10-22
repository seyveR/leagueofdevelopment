import hashlib
import hmac
import os
import secrets
import math
from datetime import timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from .db import get_db
from .models import AuthSession, LoginBucket, User, now

hasher=PasswordHasher(time_cost=3,memory_cost=65536,parallelism=2)
dummy_hash=hasher.hash(secrets.token_urlsafe(32))
secure=os.getenv('COOKIE_SECURE','false').lower()=='true'
COOKIE='liga_session'
CSRF='liga_csrf'

def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def cookie(response, name, value, age):
    response.set_cookie(name,value,max_age=age,httponly=True,secure=secure,samesite='strict',path='/')

def csrf_guard(request: Request):
    if request.method in ('GET','HEAD','OPTIONS'): return
    origin=request.headers.get('origin')
    allowed=os.getenv('PUBLIC_ORIGIN','http://127.0.0.1:8080').split(',')
    if request.headers.get('sec-fetch-site')=='cross-site' or (origin and origin not in allowed):
        raise HTTPException(403,'Недопустимый источник запроса')
    stored=request.cookies.get(CSRF,''); supplied=request.headers.get('x-csrf-token','')
    if len(stored)<32 or not hmac.compare_digest(stored,supplied): raise HTTPException(403,'Обновите страницу и повторите действие')

def current_user(request: Request, db=Depends(get_db)):
    token=request.cookies.get(COOKIE)
    session=db.scalar(select(AuthSession).where(AuthSession.token_hash==digest(token))) if token else None
    if not session or session.expires_at<=now(): raise HTTPException(401,'Войдите в приложение')
    user=db.get(User,session.user_id)
    if not user: raise HTTPException(401,'Войдите в приложение')
    return user

def parent(user=Depends(current_user)):
    if user.role!='parent': raise HTTPException(403,'Раздел доступен родителю')
    return user

def admin(user=Depends(current_user)):
    if user.role!='admin': raise HTTPException(403,'Нужны права администратора')
    return user

def login_session(db, user, response):
    token=secrets.token_urlsafe(48)
    db.add(AuthSession(user_id=user.id,token_hash=digest(token),expires_at=now()+timedelta(days=7)))
    db.commit()
    cookie(response,COOKIE,token,604800)
    csrf=secrets.token_urlsafe(32); cookie(response,CSRF,csrf,604800)
    return {'user':{'id':user.id,'email':user.email,'role':user.role},'csrf':csrf}

def throttle(db, ip, email):
    # Persistent rate limits also work with multiple API workers; row locks serialize increments.
    blocked=False
    for key,limit in [(f'ip:{ip}',30),(f'email:{email}',5)]:
        hashed=digest(key)
        db.execute(insert(LoginBucket).values(id=hashed,attempts=0,window_start=now()).on_conflict_do_nothing())
        bucket=db.scalar(select(LoginBucket).where(LoginBucket.id==hashed).with_for_update())
        if now()-bucket.window_start>timedelta(minutes=15): bucket.attempts=0; bucket.window_start=now()
        bucket.attempts+=1
        blocked=blocked or bucket.attempts>limit
    db.commit()
    if blocked: raise HTTPException(429,'Слишком много попыток. Повторите через 15 минут.')

LOGIN_FAILURE_LIMIT=15
LOGIN_COOLDOWN_SECONDS=60

def login_failure_key(email):
    # Separate namespace: old buckets counted successful logins and shared proxy IPs.
    return digest(f'login-failures-v2:{email}')

def reset_login_failures(db,email):
    bucket=db.scalar(select(LoginBucket).where(LoginBucket.id==login_failure_key(email)).with_for_update())
    if bucket:
        bucket.attempts=0
        bucket.window_start=now()
    # Persist together with the new session, never before password verification.

def reject_login(db,email):
    timestamp=now();key=login_failure_key(email)
    db.execute(insert(LoginBucket).values(id=key,attempts=0,window_start=timestamp).on_conflict_do_nothing())
    bucket=db.scalar(select(LoginBucket).where(LoginBucket.id==key).with_for_update())
    timestamp=now()
    if bucket.attempts>=LOGIN_FAILURE_LIMIT:
        remaining=LOGIN_COOLDOWN_SECONDS-(timestamp-bucket.window_start).total_seconds()
        if remaining>0:
            # Attempts during the pause do not extend it. A valid password always bypasses it.
            db.commit()
            raise HTTPException(429,'Слишком много неверных попыток. Повторите через минуту.',headers={'Retry-After':str(max(1,math.ceil(remaining)))})
        bucket.attempts=0
    bucket.attempts+=1
    blocked=bucket.attempts>=LOGIN_FAILURE_LIMIT
    if blocked:bucket.window_start=timestamp
    db.commit()
    if blocked:raise HTTPException(429,'Слишком много неверных попыток. Повторите через минуту.',headers={'Retry-After':str(LOGIN_COOLDOWN_SECONDS)})
    raise HTTPException(401,'Неверный email или пароль')

def verify(encoded,password):
    try: return hasher.verify(encoded,password)
    except (VerificationError,InvalidHashError): return False
