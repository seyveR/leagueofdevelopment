import os
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def database_url():
    return os.getenv('DATABASE_URL') or URL.create('postgresql+psycopg', username=os.getenv('DB_USER','liga'), password=os.environ['DB_PASSWORD'], host=os.getenv('DB_HOST','postgres'), database=os.getenv('DB_NAME','liga'))

engine = create_engine(database_url(), pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db
