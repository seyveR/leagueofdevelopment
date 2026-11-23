"""Retire old catalogue entries without deleting historical links."""
from uuid import uuid5,NAMESPACE_URL
from alembic import op
import sqlalchemy as sa
revision='0007'
down_revision='0006'
branch_labels=None
depends_on=None

def upgrade():
    keys=['bio','chem','bioschool','robotjunior','robot','neuro','python','school','sand','career','art','gym3','gym4','running']
    ids=[str(uuid5(NAMESPACE_URL,'liga/catalog/2026/program/'+k)) for k in keys]
    query=sa.text('UPDATE clubs SET archived=true WHERE id NOT IN :ids').bindparams(sa.bindparam('ids',expanding=True))
    op.execute(query.bindparams(ids=ids))

def downgrade():
    # Archival is intentionally retained; restoring unrelated archived cards is unsafe.
    pass
