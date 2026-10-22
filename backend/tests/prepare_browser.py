"""Creates an admin only in the isolated test database. No production defaults."""
import os
from sqlalchemy import select
from app.db import engine,SessionLocal
from app.models import User
from app.security import hasher
if engine.url.database!='liga_test':raise SystemExit('Test database required')
with SessionLocal() as db:
    for email in ['browser-admin@example.com','password-admin@example.com']:
        if not db.scalar(select(User).where(User.email==email)):
            db.add(User(email=email,password_hash=hasher.hash(os.environ['BROWSER_ADMIN_PASSWORD']),role='admin'))
    db.commit()
