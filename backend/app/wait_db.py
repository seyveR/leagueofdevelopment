import time
from sqlalchemy import text
from .db import engine
for attempt in range(60):
    try:
        with engine.connect() as db:db.execute(text('SELECT 1'))
        break
    except Exception:
        if attempt==59:raise RuntimeError('PostgreSQL is not ready') from None
        time.sleep(2)
