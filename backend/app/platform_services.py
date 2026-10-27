from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select,func
from sqlalchemy.dialects.postgresql import insert
from .models import User,Child,LoginBucket,now
from .platform_models import AccountState,Subscription,Plan,Notification,ActionLog,Organization,ProgramInfo
from .preferences import effective

def sensitive_limit(db,user,action,limit=30):
    """Per-account, per-action minute window; never counts or limits valid logins."""
    from .security import digest
    import math
    key=digest(f'action-v1:{user.id}:{action}');timestamp=now()
    db.execute(insert(LoginBucket).values(id=key,attempts=0,window_start=timestamp).on_conflict_do_nothing())
    row=db.scalar(select(LoginBucket).where(LoginBucket.id==key).with_for_update())
    if (timestamp-row.window_start).total_seconds()>=60:row.attempts=0;row.window_start=timestamp
    if row.attempts>=limit:
        remaining=max(1,math.ceil(60-(timestamp-row.window_start).total_seconds()));db.commit()
        raise HTTPException(429,'Слишком много повторов действия. Повторите через минуту.',headers={'Retry-After':str(remaining)})
    row.attempts+=1;db.commit()

def consent_required(db,user):
    state=db.get(AccountState,user.id)
    if state and not state.consent:raise HTTPException(403,'Согласие отозвано. Доступны просмотр, выгрузка и удаление данных.')

def entitlement(db,user_id):
    sub=db.get(Subscription,user_id)
    plan=db.get(Plan,sub.plan_id) if sub and sub.expires_at>now() else db.get(Plan,'free')
    return {'plan_id':plan.id if plan else 'free','name':plan.name if plan else 'Бесплатный','child_limit':plan.child_limit if plan else 1,'features':plan.features if plan else [],
            'expires_at':sub.expires_at if sub else None,'status':'active' if sub and sub.expires_at>now() else 'free','cancelled':bool(sub and sub.cancelled),'payment_mode':'simulator'}

def require_feature(db,user,feature):
    if feature not in entitlement(db,user.id)['features']:raise HTTPException(402,'Для этой функции нужна подписка. Существующие данные доступны в профиле.')

def allow_new_child(db,user):
    consent_required(db,user)
    limit=entitlement(db,user.id)['child_limit']
    count=db.scalar(select(func.count()).select_from(Child).where(Child.owner_id==user.id))
    if count>=limit:raise HTTPException(402,f'На текущем тарифе доступно профилей: {limit}. Существующие профили сохранены. Откройте «Тарифы».')

def notify(db,user_id,kind,message,key,url='/notifications',child_id=None):
    settings=effective(db,user_id,child_id)
    flag={'booking':'notify_bookings','moderation':'notify_bookings','retest':'notify_retest','subscription':'notify_subscription'}[kind]
    if not settings[flag]:return
    db.execute(insert(Notification).values(id=__import__('uuid').uuid4().hex,user_id=user_id,kind=kind,message=message,dedup_key=key,url=url,read=False,created_at=now()).on_conflict_do_nothing(index_elements=['user_id','dedup_key']))

def audit(db,user,action,entity_id,detail=''):
    db.add(ActionLog(actor_id=user.id,action=action,entity_id=entity_id,detail=detail[:1000]))

def partner_org(db,user,lock=False):
    if user.role!='partner':raise HTTPException(403,'Доступно только партнёру')
    q=select(Organization).where(Organization.owner_id==user.id)
    org=db.scalar(q.with_for_update() if lock else q)
    if not org:raise HTTPException(404,'Организация не найдена')
    return org

def owns_program(db,user,id,lock=False):
    org=partner_org(db,user)
    q=select(ProgramInfo).where(ProgramInfo.club_id==id,ProgramInfo.organization_id==org.id)
    info=db.scalar(q.with_for_update() if lock else q)
    if not info:raise HTTPException(404,'Программа не найдена')
    return info
