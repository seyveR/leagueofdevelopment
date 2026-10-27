"""Account defaults and explicit child overrides. Existing data is untouched."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('preferences',sa.Column('id',sa.String(80),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),sa.Column('child_id',sa.String(36),sa.ForeignKey('children.id',ondelete='CASCADE'),nullable=True,unique=True),sa.Column('schema_version',sa.Integer(),nullable=False),sa.Column('values',sa.JSON(),nullable=False))
    op.create_index('ix_preferences_user_id','preferences',['user_id'])
def downgrade():op.drop_table('preferences')
