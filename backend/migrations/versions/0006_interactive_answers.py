"""Keep structured original actions alongside legacy choice answers."""
from alembic import op
import sqlalchemy as sa
revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None

def upgrade():op.add_column('answers',sa.Column('payload',sa.JSON(),nullable=True))
def downgrade():op.drop_column('answers','payload')
