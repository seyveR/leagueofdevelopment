from alembic import context
from app.db import engine, Base
from app import models

if context.is_offline_mode():
    context.configure(url=engine.url.render_as_string(hide_password=False),target_metadata=Base.metadata,literal_binds=True)
    with context.begin_transaction():context.run_migrations()
else:
    with engine.connect() as conn:
        context.configure(connection=conn,target_metadata=Base.metadata)
        with context.begin_transaction():context.run_migrations()
