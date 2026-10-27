from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('test_sessions',sa.Column('task_trace',sa.JSON(),nullable=False,server_default='[]'))
    op.add_column('test_sessions',sa.Column('conditions',sa.JSON(),nullable=False,server_default='{}'))
    op.add_column('answers',sa.Column('gesture_ms',sa.Integer(),nullable=True))
def downgrade():
    op.drop_column('answers','gesture_ms');op.drop_column('test_sessions','conditions');op.drop_column('test_sessions','task_trace')
