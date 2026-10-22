from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def now(): return datetime.now(timezone.utc)
def uid(): return str(uuid4())

class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class User(Identity, Base):
    __tablename__='users'
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(16), default='parent')
    __table_args__=(CheckConstraint("role IN ('parent','admin')"),)

class AuthSession(Identity, Base):
    __tablename__='auth_sessions'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class LoginBucket(Base):
    __tablename__='login_buckets'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Child(Identity, Base):
    __tablename__='children'
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(40))
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(16))
    interests: Mapped[list] = mapped_column(JSON, default=list)
    city: Mapped[str] = mapped_column(String(80))
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str] = mapped_column(String(24))
    __table_args__=(CheckConstraint('age BETWEEN 1 AND 17'), CheckConstraint("gender IN ('male','female','unspecified')"))

class TaskSet(Identity, Base):
    __tablename__='task_sets'
    code: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(24))
    tasks: Mapped[list] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__=(UniqueConstraint('code','version'),)

class TestSession(Identity, Base):
    __tablename__='test_sessions'
    child_id: Mapped[str] = mapped_column(ForeignKey('children.id'), index=True)
    task_set_id: Mapped[str] = mapped_column(ForeignKey('task_sets.id'))
    child_snapshot: Mapped[dict] = mapped_column(JSON)
    algorithm_version: Mapped[str] = mapped_column(String(24))
    position: Mapped[int] = mapped_column(Integer, default=0)
    phase: Mapped[str] = mapped_column(String(16), default='view')
    status: Mapped[str] = mapped_column(String(16), default='in_progress')
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__=(CheckConstraint('position BETWEEN 0 AND 12'),CheckConstraint("status IN ('in_progress','completed')"))

class Answer(Identity, Base):
    __tablename__='answers'
    session_id: Mapped[str] = mapped_column(ForeignKey('test_sessions.id'), index=True)
    task_id: Mapped[str] = mapped_column(String(40))
    option_id: Mapped[str] = mapped_column(String(40))
    __table_args__=(UniqueConstraint('session_id','task_id'),)

class Result(Identity, Base):
    __tablename__='results'
    session_id: Mapped[str] = mapped_column(ForeignKey('test_sessions.id'), unique=True)
    algorithm_version: Mapped[str] = mapped_column(String(24))
    scores: Mapped[dict] = mapped_column(JSON)

class Club(Identity, Base):
    __tablename__='clubs'
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(2000))
    min_age: Mapped[int] = mapped_column(Integer)
    max_age: Mapped[int] = mapped_column(Integer)
    city: Mapped[str] = mapped_column(String(80), index=True)
    address: Mapped[str] = mapped_column(String(240))
    phone: Mapped[str] = mapped_column(String(32))
    price: Mapped[str] = mapped_column(String(120))
    photo_url: Mapped[str] = mapped_column(String(1000), default='')
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__=(CheckConstraint('min_age >= 1 AND max_age <= 17 AND min_age <= max_age'),)

class Rule(Identity, Base):
    __tablename__='recommendation_rules'
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), unique=True)
    metric: Mapped[str] = mapped_column(String(16), default='any')
    minimum: Mapped[int] = mapped_column(Integer, default=0)
    maximum: Mapped[int] = mapped_column(Integer, default=100)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    explanation: Mapped[str] = mapped_column(String(300))
    __table_args__=(CheckConstraint("metric IN ('any','attention','memory')"),CheckConstraint('minimum >= 0 AND maximum <= 100 AND minimum <= maximum'))

class Feedback(Identity, Base):
    __tablename__='feedback'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    rating: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(String(2000), default='')
    request_id: Mapped[str] = mapped_column(String(36))
    __table_args__=(UniqueConstraint('user_id','request_id'),CheckConstraint('rating BETWEEN 1 AND 5'))

class Event(Identity, Base):
    __tablename__='events'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    session_id: Mapped[str] = mapped_column(ForeignKey('test_sessions.id'))
    club_id: Mapped[str | None] = mapped_column(ForeignKey('clubs.id'), nullable=True)
    kind: Mapped[str] = mapped_column(String(32))
    request_id: Mapped[str] = mapped_column(String(80))
    __table_args__=(UniqueConstraint('user_id','request_id'),CheckConstraint("kind IN ('completed','club_open')"))
