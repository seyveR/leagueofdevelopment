from datetime import datetime,timedelta
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field,field_validator
from sqlalchemy import select
from .db import get_db
from .models import User,Child,TestSession,Result,now
from .schemas import Input
from .platform_models import Plan,Subscription,PaymentOrder,Specialist,Consultation
from .security import parent,admin
from .platform_services import entitlement,require_feature,notify,audit,consent_required
from .marketplace import data

router=APIRouter(prefix='/api',tags=['Тарифы и консультации'])

@router.get('/plans')
def plans(user=Depends(parent),db=Depends(get_db)):
    return {'items':[data(p,'id name price_rub child_limit duration_days features') for p in db.scalars(select(Plan).where(Plan.active==True).order_by(Plan.price_rub))],
            'entitlement':entitlement(db,user.id),'mode':'simulator','message':'Тестовый режим. Реальных платежей и списаний нет.'}
class OrderInput(Input):
    plan_id:str
    request_id:str=Field(pattern=r'^[a-f0-9-]{36}$')
@router.post('/payments/orders')
def order(body:OrderInput,user=Depends(parent),db=Depends(get_db)):
    from .platform_services import sensitive_limit
    sensitive_limit(db,user,'order',10)
    consent_required(db,user);db.scalar(select(User).where(User.id==user.id).with_for_update())
    old=db.scalar(select(PaymentOrder).where(PaymentOrder.user_id==user.id,PaymentOrder.request_id==body.request_id))
    if old:
        if old.plan_id!=body.plan_id:raise HTTPException(409,'Идентификатор уже использован')
        return data(old,'id plan_id price_rub status mode')
    plan=db.get(Plan,body.plan_id)
    if not plan or not plan.active or plan.id=='free':raise HTTPException(422,'Тариф недоступен')
    item=PaymentOrder(user_id=user.id,plan_id=plan.id,price_rub=plan.price_rub,request_id=body.request_id);db.add(item);db.commit()
    return data(item,'id plan_id price_rub status mode')

class SimulatedPaymentAdapter:
    """Deliberately NOT an acquirer or webhook. Only confirms a stored owned test order."""
    mode='simulator'
    def confirm(self,db,order):
        if order.mode!=self.mode:raise HTTPException(409,'Несовместимый платёжный режим')
        if order.status=='confirmed':return
        if order.status!='pending':raise HTTPException(409,'Заказ уже закрыт')
        plan=db.get(Plan,order.plan_id)
        sub=db.get(Subscription,order.user_id)
        expires=now()+timedelta(days=plan.duration_days)
        if not sub:db.add(Subscription(user_id=order.user_id,plan_id=plan.id,expires_at=expires))
        else:sub.plan_id=plan.id;sub.expires_at=expires;sub.cancelled=False
        order.status='confirmed'
        notify(db,order.user_id,'subscription','Тестовая подписка активирована. Списаний не было.',f'payment:{order.id}','/plans')
PAYMENTS=SimulatedPaymentAdapter()
@router.post('/payments/orders/{id}/simulate-confirm')
def simulate(id:str,user=Depends(parent),db=Depends(get_db)):
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    order=db.scalar(select(PaymentOrder).where(PaymentOrder.id==id,PaymentOrder.user_id==user.id).with_for_update())
    if not order:raise HTTPException(404)
    PAYMENTS.confirm(db,order);db.commit();return entitlement(db,user.id)
@router.post('/subscription/cancel')
def cancel_subscription(user=Depends(parent),db=Depends(get_db)):
    sub=db.get(Subscription,user.id)
    if sub:sub.cancelled=True
    db.commit();return entitlement(db,user.id)

class PlanInput(Input):
    name:str=Field(min_length=1,max_length=80)
    price_rub:int=Field(ge=0,le=1000000)
    child_limit:int=Field(ge=1,le=20)
    duration_days:int=Field(ge=1,le=366)
    features:list[Literal['history','consultations']]=[]
    active:bool=True
@router.get('/admin/plans')
def admin_plans(user=Depends(admin),db=Depends(get_db)):return [data(p,'id name price_rub child_limit duration_days features active') for p in db.scalars(select(Plan))]
@router.put('/admin/plans/{id}')
def edit_plan(id:str,body:PlanInput,user=Depends(admin),db=Depends(get_db)):
    if id not in ['free','premium']:raise HTTPException(404)
    if id=='free' and (body.child_limit!=1 or body.price_rub!=0):raise HTTPException(422,'Бесплатный тариф: один ребёнок и нулевая цена')
    plan=db.get(Plan,id)
    if not plan:raise HTTPException(404)
    for key,value in body.model_dump().items():setattr(plan,key,value)
    audit(db,user,'plan.edit',id);db.commit();return data(plan,'id name price_rub child_limit duration_days features active')

@router.get('/children/{id}/comparison')
def compare_history(id:str,user=Depends(parent),db=Depends(get_db)):
    require_feature(db,user,'history')
    child=db.scalar(select(Child).where(Child.id==id,Child.owner_id==user.id))
    if not child:raise HTTPException(404)
    rows=db.execute(select(TestSession,Result).join(Result).where(TestSession.child_id==id,TestSession.status=='completed').order_by(TestSession.completed_at)).all()
    groups={}
    import json
    for session,result in rows:
        key=json.dumps([session.task_set_id,session.algorithm_version,session.conditions],sort_keys=True)
        if session.task_trace:key+=':adaptive:'+json.dumps([{'difficulty':t['difficulty'],'conditions':t.get('conditions',{})} for t in session.task_trace],sort_keys=True)
        groups.setdefault(key,[]).append({'session_id':session.id,'date':session.completed_at,'scores':result.scores})
    return {'groups':list(groups.values()),'message':'Сравниваются только одинаковые наборы, версии, последовательности сложности и условия. Несопоставимые режимы разделены; это не нормативная динамика способностей.'}

class SpecialistInput(Input):
    name:str=Field(min_length=2,max_length=120)
    description:str=Field(min_length=3,max_length=2000)
    contact:str=Field(min_length=3,max_length=240)
    slots:list[datetime]=Field(default_factory=list,max_length=50)
    active:bool=True
    is_test:bool=True
    @field_validator('slots')
    @classmethod
    def timezones(cls,values):
        if any(not t.tzinfo for t in values):raise ValueError('У каждого времени должен быть часовой пояс')
        if len(set(values))!=len(values):raise ValueError('Время не должно повторяться')
        return values
@router.get('/specialists')
def specialists(user=Depends(parent),db=Depends(get_db)):
    return [data(s,'id name description contact slots is_test') for s in db.scalars(select(Specialist).where(Specialist.active==True))]
@router.get('/admin/specialists')
def admin_specialists(user=Depends(admin),db=Depends(get_db)):return [data(s,'id name description contact slots active is_test') for s in db.scalars(select(Specialist))]
@router.post('/admin/specialists')
def add_specialist(body:SpecialistInput,user=Depends(admin),db=Depends(get_db)):
    values=body.model_dump();values['slots']=[t.isoformat() for t in body.slots if t.tzinfo and t>now()]
    row=Specialist(**values);db.add(row);db.flush();audit(db,user,'specialist.create',row.id);db.commit();return data(row,'id name')
@router.put('/admin/specialists/{id}')
def edit_specialist(id:str,body:SpecialistInput,user=Depends(admin),db=Depends(get_db)):
    row=db.get(Specialist,id)
    if not row:raise HTTPException(404)
    for key,value in body.model_dump().items():setattr(row,key,[v.isoformat() for v in body.slots] if key=='slots' else value)
    audit(db,user,'specialist.edit',id);db.commit();return {'ok':True}
class ConsultInput(Input):
    specialist_id:str;starts_at:datetime;request_id:str=Field(pattern=r'^[a-f0-9-]{36}$');contact:str=Field(min_length=3,max_length=240)
@router.post('/consultations')
def consultation(body:ConsultInput,user=Depends(parent),db=Depends(get_db)):
    consent_required(db,user);require_feature(db,user,'consultations');db.scalar(select(User).where(User.id==user.id).with_for_update())
    old=db.scalar(select(Consultation).where(Consultation.user_id==user.id,Consultation.request_id==body.request_id))
    if old:
        if old.specialist_id!=body.specialist_id or old.starts_at!=body.starts_at:raise HTTPException(409,'Идентификатор уже использован')
        return data(old,'id status starts_at')
    specialist=db.scalar(select(Specialist).where(Specialist.id==body.specialist_id).with_for_update())
    if not specialist or not specialist.active:raise HTTPException(404)
    if not body.starts_at.tzinfo or body.starts_at<=now() or body.starts_at.isoformat() not in specialist.slots:raise HTTPException(409,'Время недоступно')
    taken=db.scalar(select(Consultation.id).where(Consultation.specialist_id==specialist.id,Consultation.starts_at==body.starts_at,Consultation.status!='cancelled'))
    if taken:raise HTTPException(409,'Время уже занято')
    row=Consultation(user_id=user.id,**body.model_dump());db.add(row);db.flush();notify(db,user.id,'booking','Заявка на консультацию сохранена',f'consult:{row.id}','/consultations');db.commit();return data(row,'id status starts_at')
@router.get('/consultations')
def consultations(user=Depends(parent),db=Depends(get_db)):return [{**data(c,'id specialist_id starts_at status contact'),'name':db.get(Specialist,c.specialist_id).name,'is_test':db.get(Specialist,c.specialist_id).is_test} for c in db.scalars(select(Consultation).where(Consultation.user_id==user.id))]
@router.post('/consultations/{id}/cancel')
def cancel_consultation(id:str,user=Depends(parent),db=Depends(get_db)):
    row=db.scalar(select(Consultation).where(Consultation.id==id,Consultation.user_id==user.id).with_for_update())
    if not row:raise HTTPException(404)
    row.status='cancelled';db.commit();return {'ok':True}
