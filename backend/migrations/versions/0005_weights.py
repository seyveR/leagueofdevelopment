from alembic import op
import sqlalchemy as sa
revision='0005'
down_revision='0004'
branch_labels=None
depends_on=None
def upgrade():op.create_table('recommendation_config',sa.Column('id',sa.String(40),primary_key=True),sa.Column('weights',sa.JSON(),nullable=False))
def downgrade():op.drop_table('recommendation_config')
