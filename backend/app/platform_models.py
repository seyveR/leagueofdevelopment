"""Explicit entities for the modular marketplace. IDs and foreign keys are stable."""
from datetime import datetime
from sqlalchemy import String,Integer,Boolean,DateTime,JSON,ForeignKey,UniqueConstraint,CheckConstraint,Index,text
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
from .models import Identity,now

class AccountState(Base):
    __tablename__='account_states'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    blocked:Mapped[bool]=mapped_column(Boolean,default=False)
    email_verified:Mapped[bool]=mapped_column(Boolean,default=False)
    consent:Mapped[bool]=mapped_column(Boolean,default=True)
    consent_version:Mapped[str]=mapped_column(String(40),default='account-2026-10-v1')
    withdrawn_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

class Organization(Identity,Base):
    __tablename__='organizations'
    owner_id:Mapped[str|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'),unique=True,nullable=True)
    name:Mapped[str]=mapped_column(String(160))
    description:Mapped[str]=mapped_column(String(3000),default='')
    city:Mapped[str]=mapped_column(String(80))
    contact:Mapped[str]=mapped_column(String(240))
    status:Mapped[str]=mapped_column(String(24),default='draft')
    reason:Mapped[str]=mapped_column(String(1000),default='')
    document_id:Mapped[str|None]=mapped_column(String(36),nullable=True)
    __table_args__=(CheckConstraint("status IN ('draft','pending','approved','rejected','closed')"),)

class ProgramInfo(Base):
    __tablename__='program_info'
    club_id:Mapped[str]=mapped_column(ForeignKey('clubs.id',ondelete='CASCADE'),primary_key=True)
    organization_id:Mapped[str|None]=mapped_column(ForeignKey('organizations.id'),nullable=True,index=True)
    format:Mapped[str]=mapped_column(String(16),default='offline')
    price_rub:Mapped[int]=mapped_column(Integer,default=0)
    tags:Mapped[list]=mapped_column(JSON,default=list)
    photos:Mapped[list]=mapped_column(JSON,default=list)
    schedule:Mapped[str]=mapped_column(String(300),default='Уточняется')
    promotion:Mapped[str]=mapped_column(String(500),default='')
    status:Mapped[str]=mapped_column(String(24),default='approved')
    reason:Mapped[str]=mapped_column(String(1000),default='')
    __table_args__=(CheckConstraint("format IN ('online','offline','hybrid')"),CheckConstraint('price_rub >= 0'),CheckConstraint("status IN ('draft','pending','approved','rejected','archived')"))

class TrialSlot(Identity,Base):
    __tablename__='trial_slots'
    club_id:Mapped[str]=mapped_column(ForeignKey('clubs.id',ondelete='CASCADE'),index=True)
    starts_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    capacity:Mapped[int]=mapped_column(Integer,default=10)
    enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    __table_args__=(UniqueConstraint('club_id','starts_at'),CheckConstraint('capacity BETWEEN 1 AND 100'))

class Booking(Identity,Base):
    __tablename__='bookings'
    parent_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    child_id:Mapped[str|None]=mapped_column(ForeignKey('children.id',ondelete='SET NULL'),nullable=True)
    club_id:Mapped[str]=mapped_column(ForeignKey('clubs.id'),index=True)
    slot_id:Mapped[str]=mapped_column(ForeignKey('trial_slots.id'))
    status:Mapped[str]=mapped_column(String(32),default='new')
    contact:Mapped[str]=mapped_column(String(240))
    snapshot:Mapped[dict]=mapped_column(JSON)
    consent_version:Mapped[str]=mapped_column(String(40),default='booking-2026-10-v1')
    note:Mapped[str]=mapped_column(String(1000),default='')
    request_id:Mapped[str]=mapped_column(String(36))
    __table_args__=(UniqueConstraint('parent_id','request_id'),CheckConstraint("status IN ('new','accepted','rejected','completed','cancelled','cancellation_requested','ended')"),Index('uq_booking_active','child_id','slot_id',unique=True,postgresql_where=text("status IN ('new','accepted','completed','cancellation_requested')")))

class BookingEvent(Identity,Base):
    __tablename__='booking_events'
    booking_id:Mapped[str]=mapped_column(ForeignKey('bookings.id',ondelete='CASCADE'),index=True)
    actor_id:Mapped[str|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'),nullable=True)
    status:Mapped[str]=mapped_column(String(32))
    note:Mapped[str]=mapped_column(String(1000),default='')

class Favorite(Base):
    __tablename__='favorites'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    club_id:Mapped[str]=mapped_column(ForeignKey('clubs.id',ondelete='CASCADE'),primary_key=True)

class Review(Identity,Base):
    __tablename__='reviews'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    club_id:Mapped[str]=mapped_column(ForeignKey('clubs.id',ondelete='CASCADE'),index=True)
    rating:Mapped[int]=mapped_column(Integer)
    message:Mapped[str]=mapped_column(String(2000))
    status:Mapped[str]=mapped_column(String(24),default='pending')
    reason:Mapped[str]=mapped_column(String(1000),default='')
    __table_args__=(UniqueConstraint('user_id','club_id'),CheckConstraint('rating BETWEEN 1 AND 5'),CheckConstraint("status IN ('pending','published','rejected')"))

class MediaFile(Identity,Base):
    __tablename__='media_files'
    owner_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    path:Mapped[str]=mapped_column(String(80),unique=True)
    mime:Mapped[str]=mapped_column(String(80))
    private:Mapped[bool]=mapped_column(Boolean,default=False)
    size:Mapped[int]=mapped_column(Integer)

class Notification(Identity,Base):
    __tablename__='notifications'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    kind:Mapped[str]=mapped_column(String(24))
    message:Mapped[str]=mapped_column(String(500))
    url:Mapped[str]=mapped_column(String(240),default='/profile')
    read:Mapped[bool]=mapped_column(Boolean,default=False)
    dedup_key:Mapped[str]=mapped_column(String(160))
    __table_args__=(UniqueConstraint('user_id','dedup_key'),)

class Plan(Base):
    __tablename__='plans'
    id:Mapped[str]=mapped_column(String(40),primary_key=True)
    name:Mapped[str]=mapped_column(String(80))
    price_rub:Mapped[int]=mapped_column(Integer)
    child_limit:Mapped[int]=mapped_column(Integer)
    duration_days:Mapped[int]=mapped_column(Integer,default=30)
    features:Mapped[list]=mapped_column(JSON,default=list)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    __table_args__=(CheckConstraint('price_rub >= 0 AND child_limit BETWEEN 1 AND 20 AND duration_days BETWEEN 1 AND 366'),)

class Subscription(Base):
    __tablename__='subscriptions'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    plan_id:Mapped[str]=mapped_column(ForeignKey('plans.id'))
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    cancelled:Mapped[bool]=mapped_column(Boolean,default=False)

class PaymentOrder(Identity,Base):
    __tablename__='payment_orders'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    plan_id:Mapped[str]=mapped_column(ForeignKey('plans.id'))
    price_rub:Mapped[int]=mapped_column(Integer)
    status:Mapped[str]=mapped_column(String(16),default='pending')
    mode:Mapped[str]=mapped_column(String(24),default='simulator')
    request_id:Mapped[str]=mapped_column(String(36))
    __table_args__=(UniqueConstraint('user_id','request_id'),CheckConstraint("status IN ('pending','confirmed','cancelled')"))

class Specialist(Identity,Base):
    __tablename__='specialists'
    name:Mapped[str]=mapped_column(String(120))
    description:Mapped[str]=mapped_column(String(2000))
    contact:Mapped[str]=mapped_column(String(240))
    slots:Mapped[list]=mapped_column(JSON,default=list)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    is_test:Mapped[bool]=mapped_column(Boolean,default=True)

class Consultation(Identity,Base):
    __tablename__='consultations'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    specialist_id:Mapped[str]=mapped_column(ForeignKey('specialists.id'))
    starts_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    status:Mapped[str]=mapped_column(String(16),default='new')
    contact:Mapped[str]=mapped_column(String(240))
    request_id:Mapped[str]=mapped_column(String(36))
    __table_args__=(UniqueConstraint('user_id','request_id'),Index('uq_consultation_active','specialist_id','starts_at',unique=True,postgresql_where=text("status <> 'cancelled'")))

class ActionLog(Identity,Base):
    __tablename__='action_log'
    actor_id:Mapped[str|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'),nullable=True)
    action:Mapped[str]=mapped_column(String(80))
    entity_id:Mapped[str]=mapped_column(String(80))
    detail:Mapped[str]=mapped_column(String(1000),default='')

class AccessToken(Identity,Base):
    __tablename__='access_tokens'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    kind:Mapped[str]=mapped_column(String(16))
    token_hash:Mapped[str]=mapped_column(String(64),unique=True)
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    used:Mapped[bool]=mapped_column(Boolean,default=False)
