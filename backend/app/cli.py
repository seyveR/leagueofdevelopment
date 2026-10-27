import argparse,getpass,secrets
from datetime import timedelta
from pydantic import TypeAdapter,EmailStr
from sqlalchemy import select
from .db import SessionLocal
from .models import User,now
from .security import hasher,digest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['create-admin','issue-reset-link','issue-verification-link']);parser.add_argument('--email',required=True);args=parser.parse_args()
    email=str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    if args.command!='create-admin':
        from .platform_models import AccessToken
        with SessionLocal() as db:
            user=db.scalar(select(User).where(User.email==email))
            if not user:raise SystemExit('Учётная запись не найдена')
            kind='reset' if args.command=='issue-reset-link' else 'verify'
            for row in db.scalars(select(AccessToken).where(AccessToken.user_id==user.id,AccessToken.kind==kind,AccessToken.used==False)):row.used=True
            token=secrets.token_urlsafe(40);db.add(AccessToken(user_id=user.id,kind=kind,token_hash=digest(token),expires_at=now()+timedelta(minutes=30)));db.commit()
        print('Локальная одноразовая ссылка, действует 30 минут. Email не отправлялся:')
        print(f'http://127.0.0.1:8080/recovery?kind={kind}&token={token}')
        return
    password=getpass.getpass('Пароль администратора (не менее 10 символов): ')
    if len(password)<10 or len(password)>128:raise SystemExit('Пароль должен содержать от 10 до 128 символов')
    if password!=getpass.getpass('Повторите пароль: '):raise SystemExit('Пароли не совпадают')
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email==email)):raise SystemExit('Email уже занят. Роль существующей записи не изменялась.')
        db.add(User(email=email,password_hash=hasher.hash(password),role='admin'));db.commit()
    print('Администратор создан')
if __name__=='__main__':main()
