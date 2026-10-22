import argparse,getpass
from pydantic import TypeAdapter,EmailStr
from sqlalchemy import select
from .db import SessionLocal
from .models import User
from .security import hasher

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['create-admin']);parser.add_argument('--email',required=True);args=parser.parse_args()
    email=str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    password=getpass.getpass('Пароль администратора (не менее 10 символов): ')
    if len(password)<10 or len(password)>128:raise SystemExit('Пароль должен содержать от 10 до 128 символов')
    if password!=getpass.getpass('Повторите пароль: '):raise SystemExit('Пароли не совпадают')
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email==email)):raise SystemExit('Email уже занят. Роль существующей записи не изменялась.')
        db.add(User(email=email,password_hash=hasher.hash(password),role='admin'));db.commit()
    print('Администратор создан')
if __name__=='__main__':main()
