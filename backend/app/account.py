import json,secrets
from datetime import timedelta
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from pydantic import EmailStr,Field
from sqlalchemy import select,delete,func
from .db import get_db
from .models import User,Child,AuthSession,TestSession,Answer,Result,Event,Feedback,Club,now
from .schemas import Input
from .security import current_user,parent,admin,throttle,hasher,verify,digest,COOKIE,CSRF
from .platform_models import AccountState,AccessToken,Notification,Organization,ProgramInfo,Booking,Subscription,ActionLog,MediaFile,Consultation,Plan,PaymentOrder
from .platform_services import notify,audit,entitlement
from .marketplace import data

router=APIRouter(prefix='/api',tags=['Аккаунт и уведомления'])
@router.post('/notifications/sync')
def sync_notifications(user=Depends(current_user),db=Depends(get_db)):
    if user.role=='parent':
        for child in db.scalars(select(Child).where(Child.owner_id==user.id)):
            latest=db.scalar(select(TestSession).where(TestSession.child_id==child.id,TestSession.status=='completed').order_by(TestSession.completed_at.desc()).limit(1))
            if latest and latest.completed_at<now()-timedelta(days=30):notify(db,user.id,'retest','Можно повторить ознакомительные задания.',f'retest:{child.id}:{latest.id}','/tests',child.id)
        sub=db.get(Subscription,user.id)
        if sub and sub.expires_at<=now():notify(db,user.id,'subscription','Срок тестовой подписки истёк. Сохранённые данные доступны.',f'expired:{sub.expires_at.isoformat()}','/plans')
    db.commit();return {'ok':True}
@router.get('/notifications')
def notifications(user=Depends(current_user),db=Depends(get_db)):
    return [data(n,'id kind message url read created_at') for n in db.scalars(select(Notification).where(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(200))]
@router.post('/notifications/{id}/read')
def read_notification(id:str,user=Depends(current_user),db=Depends(get_db)):
    row=db.scalar(select(Notification).where(Notification.id==id,Notification.user_id==user.id))
    if not row:raise HTTPException(404)
    row.read=True;db.commit();return {'ok':True}

class TokenRequest(Input):email:EmailStr
class TokenConsume(Input):token:str=Field(min_length=32,max_length=128)
class ResetInput(TokenConsume):password:str=Field(min_length=10,max_length=128)
@router.post('/auth/recovery')
def recovery(body:TokenRequest,request:Request,db=Depends(get_db)):
    throttle(db,request.client.host,'recovery:'+str(body.email).lower())
    # No link is returned publicly and no email delivery is claimed.
    return {'message':'Email-доставка не подключена. Для локальной проверки администратор может выдать одноразовую ссылку через команду управления.'}
@router.post('/auth/reset')
def reset_password(body:ResetInput,response:Response,db=Depends(get_db)):
    row=db.scalar(select(AccessToken).where(AccessToken.token_hash==digest(body.token),AccessToken.kind=='reset').with_for_update())
    if not row or row.used or row.expires_at<=now():raise HTTPException(400,'Ссылка недействительна или истекла')
    user=db.scalar(select(User).where(User.id==row.user_id).with_for_update());user.password_hash=hasher.hash(body.password);row.used=True
    db.execute(delete(AuthSession).where(AuthSession.user_id==user.id));db.commit();response.delete_cookie(COOKIE,path='/');response.delete_cookie(CSRF,path='/');return {'ok':True}
@router.post('/auth/verify-email')
def verify_email(body:TokenConsume,db=Depends(get_db)):
    row=db.scalar(select(AccessToken).where(AccessToken.token_hash==digest(body.token),AccessToken.kind=='verify').with_for_update())
    if not row or row.used or row.expires_at<=now():raise HTTPException(400,'Ссылка недействительна или истекла')
    state=db.get(AccountState,row.user_id)
    if not state:state=AccountState(user_id=row.user_id);db.add(state)
    state.email_verified=True;row.used=True;db.commit();return {'ok':True}
@router.get('/account')
def account(user=Depends(current_user),db=Depends(get_db)):
    state=db.get(AccountState,user.id)
    return {'email':user.email,'email_verified':bool(state and state.email_verified),'consent':state.consent if state else True,'consent_version':state.consent_version if state else 'legacy-child-consent','delivery_mode':'local-command-only','payment_mode':'simulator'}
class ConsentInput(Input):consent:bool
@router.put('/account/consent')
def consent(body:ConsentInput,user=Depends(current_user),db=Depends(get_db)):
    row=db.get(AccountState,user.id)
    if not row:row=AccountState(user_id=user.id);db.add(row)
    row.consent=body.consent;row.consent_version='account-2026-10-v1';row.withdrawn_at=None if body.consent else now();db.commit();return account(user,db)
@router.get('/account/export')
def export(user=Depends(current_user),db=Depends(get_db)):
    children=db.scalars(select(Child).where(Child.owner_id==user.id)).all();ids=[c.id for c in children]
    sessions=db.scalars(select(TestSession).where(TestSession.child_id.in_(ids))).all();session_ids=[s.id for s in sessions]
    result={'schema_version':1,'user':data(user,'id email role'),'children':[data(c,'id name age gender city interests consent_at consent_version') for c in children],
            'sessions':[data(s,'id task_set_id child_snapshot algorithm_version conditions task_trace created_at completed_at status') for s in sessions],
            'answers':[data(a,'session_id task_id option_id gesture_ms created_at') for a in db.scalars(select(Answer).where(Answer.session_id.in_(session_ids)))],
            'results':[data(r,'session_id scores algorithm_version') for r in db.scalars(select(Result).where(Result.session_id.in_(session_ids)))],
            'bookings':[data(b,'id club_id slot_id status contact snapshot created_at') for b in db.scalars(select(Booking).where(Booking.parent_id==user.id))]}
    # Correct-answer keys are private to the platform, not part of a personal export.
    for s in result['sessions']:
        s['task_trace']=[{k:v for k,v in t.items() if k!='task'} for t in s['task_trace']]
    from .preferences import Preference
    from .platform_models import Favorite,Review,Consultation
    result['account']=account(user,db)
    result['settings']=[data(p,'id child_id schema_version values') for p in db.scalars(select(Preference).where(Preference.user_id==user.id))]
    result['favorites']=[f.club_id for f in db.scalars(select(Favorite).where(Favorite.user_id==user.id))]
    result['reviews']=[data(r,'id club_id rating message status reason created_at') for r in db.scalars(select(Review).where(Review.user_id==user.id))]
    result['notifications']=[data(n,'id kind message read created_at') for n in db.scalars(select(Notification).where(Notification.user_id==user.id))]
    result['consultations']=[data(c,'id specialist_id starts_at contact status created_at') for c in db.scalars(select(Consultation).where(Consultation.user_id==user.id))]
    result['payment_orders']=[data(o,'id plan_id price_rub status mode created_at') for o in db.scalars(select(PaymentOrder).where(PaymentOrder.user_id==user.id))]
    result['subscription']=entitlement(db,user.id)
    result['files']=[data(f,'id mime private size created_at') for f in db.scalars(select(MediaFile).where(MediaFile.owner_id==user.id))]
    org=db.scalar(select(Organization).where(Organization.owner_id==user.id))
    if org:
        result['organization']=data(org,'id name description city contact status reason document_id')
        result['program_details']=[data(p,'club_id format price_rub tags photos schedule promotion status reason') for p in db.scalars(select(ProgramInfo).where(ProgramInfo.organization_id==org.id))]
    return result
class DeleteInput(Input):password:str=Field(min_length=1,max_length=128);confirmation:str
@router.post('/account/delete')
def delete_account(body:DeleteInput,response:Response,user=Depends(current_user),db=Depends(get_db)):
    from .platform_services import sensitive_limit
    sensitive_limit(db,user,'delete-account',5)
    if user.role=='admin':raise HTTPException(403,'Администратор не удаляет свою запись через этот экран')
    if body.confirmation!='УДАЛИТЬ' or not verify(user.password_hash,body.password):raise HTTPException(400,'Проверьте пароль и подтверждение')
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    org=db.scalar(select(Organization).where(Organization.owner_id==user.id))
    if org:
        org.status='closed';org.owner_id=None;org.contact='Удалено';org.description='';org.document_id=None
        for info in db.scalars(select(ProgramInfo).where(ProgramInfo.organization_id==org.id)):
            db.get(Club,info.club_id).archived=True;info.status='archived';info.photos=[]
    ids=select(Child.id).where(Child.owner_id==user.id);sessions=select(TestSession.id).where(TestSession.child_id.in_(ids))
    db.execute(delete(Event).where((Event.user_id==user.id)|(Event.session_id.in_(sessions))))
    db.execute(delete(Result).where(Result.session_id.in_(sessions)));db.execute(delete(Answer).where(Answer.session_id.in_(sessions)))
    db.execute(delete(TestSession).where(TestSession.child_id.in_(ids)));db.execute(delete(Feedback).where(Feedback.user_id==user.id))
    files=db.scalars(select(MediaFile).where(MediaFile.owner_id==user.id)).all();keys=[f.path for f in files]
    db.delete(user);db.commit()
    from .storage import FILES
    for key in keys:FILES.remove(key)
    response.delete_cookie(COOKIE,path='/');response.delete_cookie(CSRF,path='/');return {'ok':True}

@router.get('/admin/users')
def users(user=Depends(admin),db=Depends(get_db)):
    return [{**data(u,'id email role created_at'),'blocked':bool(db.get(AccountState,u.id) and db.get(AccountState,u.id).blocked)} for u in db.scalars(select(User).order_by(User.created_at.desc()).limit(500))]
class BlockInput(Input):blocked:bool
@router.post('/admin/users/{id}/block')
def block(id:str,body:BlockInput,user=Depends(admin),db=Depends(get_db)):
    if id==user.id:raise HTTPException(409,'Нельзя заблокировать свою учётную запись')
    target=db.get(User,id)
    if not target:raise HTTPException(404)
    state=db.get(AccountState,id)
    if not state:state=AccountState(user_id=id);db.add(state)
    state.blocked=body.blocked
    if body.blocked:db.execute(delete(AuthSession).where(AuthSession.user_id==id))
    audit(db,user,'user.block',id,str(body.blocked));db.commit();return {'ok':True}
@router.get('/admin/audit')
def audit_log(user=Depends(admin),db=Depends(get_db)):return [data(a,'id actor_id action entity_id detail created_at') for a in db.scalars(select(ActionLog).order_by(ActionLog.created_at.desc()).limit(200))]
@router.get('/admin/platform-stats')
def platform_stats(user=Depends(admin),db=Depends(get_db)):
    def count(model,condition=None):
        q=select(func.count()).select_from(model)
        return db.scalar(q.where(condition) if condition is not None else q)
    return {'users':count(User),'organizations':count(Organization),'bookings':count(Booking),'accepted':count(Booking,Booking.status=='accepted'),'completed_trials':count(Booking,Booking.status=='completed'),
            'simulated_payments':count(PaymentOrder,PaymentOrder.status=='confirmed'),'real_revenue_rub':0,'payment_mode':'simulator'}

@router.get('/admin/task-sets')
def task_sets(user=Depends(admin),db=Depends(get_db)):
    from .models import TaskSet
    return [{**data(s,'id code version active'),'task_count':len(s.tasks)} for s in db.scalars(select(TaskSet).order_by(TaskSet.code,TaskSet.version))]
class Availability(Input):active:bool
@router.put('/admin/task-sets/{id}/availability')
def task_availability(id:str,body:Availability,user=Depends(admin),db=Depends(get_db)):
    from .models import TaskSet
    row=db.get(TaskSet,id)
    if not row:raise HTTPException(404)
    row.active=body.active;audit(db,user,'task_set.availability',id,str(body.active));db.commit();return {'ok':True}
