from alembic import op
import sqlalchemy as sa
revision='0008'
down_revision='0007'
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    for constraint in sa.inspect(bind).get_check_constraints('test_sessions'):
        if 'position' in constraint['sqltext']:
            op.drop_constraint(constraint['name'],'test_sessions',type_='check')
    op.create_check_constraint('test_sessions_position_range','test_sessions','position BETWEEN 0 AND 50')

def downgrade():
    if op.get_bind().execute(sa.text('SELECT count(*) FROM test_sessions WHERE position>12')).scalar():raise RuntimeError('Long journeys exist; preserve their data before downgrade')
    op.drop_constraint('test_sessions_position_range','test_sessions',type_='check')
    op.create_check_constraint('test_sessions_position_range','test_sessions','position BETWEEN 0 AND 12')
