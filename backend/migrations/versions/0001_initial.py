"""Initial immutable schema for MVP-lite."""
from alembic import op
import sqlalchemy as sa
revision='0001'
down_revision=None
branch_labels=None
depends_on=None

def identity():return [sa.Column('id',sa.String(36),primary_key=True),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False)]
def fk(name,target,**kw):return sa.Column(name,sa.String(36),sa.ForeignKey(target,**kw),nullable=False)
def col(name,typ,**kw):return sa.Column(name,typ,nullable=False,**kw)
def upgrade():
    op.create_table('users',*identity(),col('email',sa.String(254)),col('password_hash',sa.String(512)),col('role',sa.String(16)),sa.UniqueConstraint('email'),sa.CheckConstraint("role IN ('parent','admin')"))
    op.create_table('auth_sessions',*identity(),fk('user_id','users.id',ondelete='CASCADE'),col('token_hash',sa.String(64)),col('expires_at',sa.DateTime(timezone=True)),sa.UniqueConstraint('token_hash'))
    op.create_table('login_buckets',col('id',sa.String(64),primary_key=True),col('attempts',sa.Integer()),col('window_start',sa.DateTime(timezone=True)))
    op.create_table('children',*identity(),fk('owner_id','users.id',ondelete='CASCADE'),col('name',sa.String(40)),col('age',sa.Integer()),col('gender',sa.String(16)),col('interests',sa.JSON()),col('city',sa.String(80)),col('consent_at',sa.DateTime(timezone=True)),col('consent_version',sa.String(24)),sa.CheckConstraint('age BETWEEN 1 AND 17'),sa.CheckConstraint("gender IN ('male','female','unspecified')"))
    op.create_table('task_sets',*identity(),col('code',sa.String(64)),col('version',sa.String(24)),col('tasks',sa.JSON()),col('active',sa.Boolean()),sa.UniqueConstraint('code','version'))
    op.create_table('test_sessions',*identity(),fk('child_id','children.id'),fk('task_set_id','task_sets.id'),col('child_snapshot',sa.JSON()),col('algorithm_version',sa.String(24)),col('position',sa.Integer()),col('phase',sa.String(16)),col('status',sa.String(16)),sa.Column('completed_at',sa.DateTime(timezone=True)),sa.CheckConstraint('position BETWEEN 0 AND 12'),sa.CheckConstraint("status IN ('in_progress','completed')"))
    op.create_table('answers',*identity(),fk('session_id','test_sessions.id'),col('task_id',sa.String(40)),col('option_id',sa.String(40)),sa.UniqueConstraint('session_id','task_id'))
    op.create_table('results',*identity(),fk('session_id','test_sessions.id'),col('algorithm_version',sa.String(24)),col('scores',sa.JSON()),sa.UniqueConstraint('session_id'))
    op.create_table('clubs',*identity(),col('name',sa.String(120)),col('description',sa.String(2000)),col('min_age',sa.Integer()),col('max_age',sa.Integer()),col('city',sa.String(80)),col('address',sa.String(240)),col('phone',sa.String(32)),col('price',sa.String(120)),col('photo_url',sa.String(1000)),col('archived',sa.Boolean()),sa.CheckConstraint('min_age >= 1 AND max_age <= 17 AND min_age <= max_age'))
    op.create_table('recommendation_rules',*identity(),fk('club_id','clubs.id'),col('metric',sa.String(16)),col('minimum',sa.Integer()),col('maximum',sa.Integer()),col('priority',sa.Integer()),col('explanation',sa.String(300)),sa.UniqueConstraint('club_id'),sa.CheckConstraint("metric IN ('any','attention','memory')"),sa.CheckConstraint('minimum >= 0 AND maximum <= 100 AND minimum <= maximum'))
    op.create_table('feedback',*identity(),fk('user_id','users.id'),col('rating',sa.Integer()),col('message',sa.String(2000)),col('request_id',sa.String(36)),sa.UniqueConstraint('user_id','request_id'),sa.CheckConstraint('rating BETWEEN 1 AND 5'))
    op.create_table('events',*identity(),fk('user_id','users.id'),fk('session_id','test_sessions.id'),sa.Column('club_id',sa.String(36),sa.ForeignKey('clubs.id')),col('kind',sa.String(32)),col('request_id',sa.String(80)),sa.UniqueConstraint('user_id','request_id'),sa.CheckConstraint("kind IN ('completed','club_open')"))
    for table,column in [('auth_sessions','user_id'),('children','owner_id'),('test_sessions','child_id'),('answers','session_id'),('clubs','city')]:op.create_index(f'ix_{table}_{column}',table,[column])

def downgrade():
    for table in ['events','feedback','recommendation_rules','clubs','results','answers','test_sessions','task_sets','children','login_buckets','auth_sessions','users']:op.drop_table(table)
