import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from fastapi.testclient import TestClient
from app.db import engine,Base,SessionLocal
from app.main import app
from app.seed import seed

@pytest.fixture(scope='session',autouse=True)
def test_database_only():
    if not engine.url.database or not engine.url.database.endswith('_test'):
        pytest.exit('Refusing to run: database name must end in _test. Never use the application database.')
    command.upgrade(Config('alembic.ini'),'head')

@pytest.fixture(autouse=True)
def clean(test_database_only):
    with engine.begin() as connection:
        connection.execute(text('TRUNCATE '+','.join('"'+table.name+'"' for table in Base.metadata.sorted_tables)+' CASCADE'))
    with SessionLocal() as db:seed(db)

@pytest.fixture
def client():
    with TestClient(app) as client:yield client

def csrf(client):
    value=client.get('/api/auth/session').json()
    client.headers['X-CSRF-Token']=value['csrf']
    return value

def register(client,email='parent@example.com'):
    csrf(client)
    response=client.post('/api/auth/register',json={'email':email,'password':'test-password-123'})
    assert response.status_code==200,response.text
    client.headers['X-CSRF-Token']=response.json()['csrf']
    return response.json()['user']
