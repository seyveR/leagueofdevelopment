import csv,io,secrets,struct,zlib
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,Request,Response,Query
from fastapi.responses import FileResponse
from pydantic import Field,model_validator
from sqlalchemy import select,func,delete
from .db import get_db
from .models import User,Child,Club,Rule,Result,TestSession,now
from .schemas import Input,Credentials,ClubInput
from .security import current_user,parent,admin,hasher,login_session,throttle
from .platform_models import Organization,ProgramInfo,TrialSlot,Booking,BookingEvent,Favorite,Review,MediaFile
from .platform_services import partner_org,owns_program,consent_required,notify,audit

router=APIRouter(prefix='/api',tags=['Маркетплейс'])
def data(row,fields):return {key:getattr(row,key) for key in fields.split()}
ORG_FIELDS='id name description city contact status reason document_id'
INFO_FIELDS='club_id organization_id format price_rub tags photos schedule promotion status reason'
CLUB_FIELDS='id name description min_age max_age city address phone price photo_url archived'

class OrganizationInput(Input):
    name:str=Field(min_length=2,max_length=160)
    description:str=Field(default='',max_length=3000)
    city:str=Field(min_length=1,max_length=80)
    contact:str=Field(min_length=3,max_length=240)
    document_id:str|None=None
class PartnerInput(Credentials):
    organization:OrganizationInput
    consent:bool
@router.post('/partner/register')
def register_partner(body:PartnerInput,request:Request,response:Response,db=Depends(get_db)):
    if not body.consent:raise HTTPException(422,'Подтвердите согласие на обработку контактов')
    email=str(body.email).lower();throttle(db,request.client.host,'partner:'+email)
    if db.scalar(select(User).where(User.email==email)):raise HTTPException(409,'Email уже зарегистрирован')
    if body.organization.document_id:raise HTTPException(422,'Документ можно добавить после регистрации')
    user=User(email=email,password_hash=hasher.hash(body.password),role='partner');db.add(user);db.flush()
    db.add(Organization(owner_id=user.id,**body.organization.model_dump(),status='draft'))
    return login_session(db,user,response)
@router.get('/partner/organization')
def organization(user=Depends(current_user),db=Depends(get_db)):return data(partner_org(db,user),ORG_FIELDS)
@router.put('/partner/organization')
def save_organization(body:OrganizationInput,user=Depends(current_user),db=Depends(get_db)):
    org=partner_org(db,user,True)
    if body.document_id:
        file=db.get(MediaFile,body.document_id)
        if not file or file.owner_id!=user.id or not file.private:raise HTTPException(422,'Недоступный документ')
    for key,value in body.model_dump().items():setattr(org,key,value)
    org.status='pending';org.reason='';audit(db,user,'organization.submit',org.id)
    # Editing an approved organisation suspends new enrolments until moderation.
    db.commit();return data(org,ORG_FIELDS)
@router.get('/admin/organizations')
def organizations(user=Depends(admin),db=Depends(get_db)):return [data(o,ORG_FIELDS) for o in db.scalars(select(Organization).order_by(Organization.created_at.desc()))]
class Decision(Input):
    approved:bool
    reason:str=Field(default='',max_length=1000)
    @model_validator(mode='after')
    def rejection_reason(self):
        if not self.approved and not self.reason:raise ValueError('Укажите причину отказа')
        return self
@router.post('/admin/organizations/{id}/decision')
def decide_org(id:str,body:Decision,user=Depends(admin),db=Depends(get_db)):
    org=db.scalar(select(Organization).where(Organization.id==id).with_for_update())
    if not org:raise HTTPException(404)
    org.status='approved' if body.approved else 'rejected';org.reason=body.reason
    if org.owner_id:notify(db,org.owner_id,'moderation',f'Организация: '+('одобрена' if body.approved else 'отклонена')+f'. {org.reason}',f'org:{id}:{uuid4()}','/partner')
    audit(db,user,'organization.decision',id,org.status);db.commit();return data(org,ORG_FIELDS)

class ProgramInput(ClubInput):
    format:Literal['online','offline','hybrid']='offline'
    price_rub:int=Field(ge=0,le=1000000)
    tags:list[str]=Field(default_factory=list,max_length=12)
    photos:list[str]=Field(default_factory=list,max_length=6)
    schedule:str=Field(default='Уточняется',max_length=300)
    promotion:str=Field(default='',max_length=500)

def program_data(db,club):
    info=db.get(ProgramInfo,club.id)
    return {**data(club,CLUB_FIELDS),'details':data(info,INFO_FIELDS) if info else None}
def validate_photos(db,user,photos):
    for id in photos:
        file=db.get(MediaFile,id)
        if not file or file.owner_id!=user.id or file.private:raise HTTPException(422,'Недоступная фотография')
@router.get('/partner/programs')
def partner_programs(user=Depends(current_user),db=Depends(get_db)):
    org=partner_org(db,user)
    clubs=db.scalars(select(Club).join(ProgramInfo).where(ProgramInfo.organization_id==org.id).order_by(Club.created_at.desc()))
    return [program_data(db,c) for c in clubs]
@router.post('/partner/programs')
def add_program(body:ProgramInput,user=Depends(current_user),db=Depends(get_db)):
    org=partner_org(db,user,True);consent_required(db,user);validate_photos(db,user,body.photos)
    if body.request_id:
        old=db.get(Club,body.request_id)
        if old:owns_program(db,user,old.id);return program_data(db,old)
    values=body.model_dump();extra={k:values.pop(k) for k in ['format','price_rub','tags','photos','schedule','promotion']};request=values.pop('request_id')
    values['archived']=True;club=Club(**values,**({'id':request} if request else {}));db.add(club);db.flush()
    db.add(ProgramInfo(club_id=club.id,organization_id=org.id,status='pending',**extra));db.add(Rule(club_id=club.id,metric='any',explanation='Программа соответствует выбранным условиям.'))
    audit(db,user,'program.create',club.id);db.commit();return program_data(db,club)
@router.put('/partner/programs/{id}')
def edit_program(id:str,body:ProgramInput,user=Depends(current_user),db=Depends(get_db)):
    info=owns_program(db,user,id,True);validate_photos(db,user,body.photos);club=db.get(Club,id)
    for key,value in body.model_dump(exclude={'request_id'}).items():
        if key in ['format','price_rub','tags','photos','schedule','promotion']:setattr(info,key,value)
        else:setattr(club,key,value)
    info.status='archived' if body.archived else 'pending';info.reason='';club.archived=True
    audit(db,user,'program.edit',id,info.status);db.commit();return program_data(db,club)
@router.get('/admin/programs')
def admin_programs(user=Depends(admin),db=Depends(get_db)):return [program_data(db,c) for c in db.scalars(select(Club).order_by(Club.created_at.desc()))]
@router.post('/admin/programs/{id}/decision')
def decide_program(id:str,body:Decision,user=Depends(admin),db=Depends(get_db)):
    info=db.scalar(select(ProgramInfo).where(ProgramInfo.club_id==id).with_for_update())
    if not info:raise HTTPException(404)
    org=db.get(Organization,info.organization_id) if info.organization_id else None
    if body.approved and org and org.status!='approved':raise HTTPException(409,'Сначала одобрите организацию')
    info.status='approved' if body.approved else 'rejected';info.reason=body.reason;db.get(Club,id).archived=not body.approved
    if org and org.owner_id:notify(db,org.owner_id,'moderation',f'Программа: '+('одобрена' if body.approved else 'отклонена')+f'. {info.reason}',f'program:{id}:{uuid4()}','/partner/programs')
    audit(db,user,'program.decision',id,info.status);db.commit();return {'ok':True}

class SlotInput(Input):
    starts_at:datetime
    capacity:int=Field(default=10,ge=1,le=100)
@router.post('/partner/programs/{id}/slots')
def add_slot(id:str,body:SlotInput,user=Depends(current_user),db=Depends(get_db)):
    owns_program(db,user,id,True)
    if not body.starts_at.tzinfo or body.starts_at<=now():raise HTTPException(422,'Укажите будущее время с часовым поясом')
    slot=TrialSlot(club_id=id,**body.model_dump());db.add(slot);db.commit();return data(slot,'id club_id starts_at capacity enabled')
@router.get('/partner/programs/{id}/slots')
def own_slots(id:str,user=Depends(current_user),db=Depends(get_db)):
    owns_program(db,user,id)
    return [data(s,'id starts_at capacity enabled') for s in db.scalars(select(TrialSlot).where(TrialSlot.club_id==id).order_by(TrialSlot.starts_at))]
@router.delete('/partner/slots/{id}')
def disable_slot(id:str,user=Depends(current_user),db=Depends(get_db)):
    slot=db.scalar(select(TrialSlot).where(TrialSlot.id==id).with_for_update())
    if not slot:raise HTTPException(404)
    owns_program(db,user,slot.club_id)
    occupied=db.scalar(select(func.count()).select_from(Booking).where(Booking.slot_id==id,Booking.status.in_(['new','accepted','completed','cancellation_requested'])))
    if occupied:raise HTTPException(409,'Сначала обработайте заявки на это время')
    slot.enabled=False;db.commit();return {'ok':True}

def public_program(db,id):
    club=db.get(Club,id);info=db.get(ProgramInfo,id)
    org=db.get(Organization,info.organization_id) if info and info.organization_id else None
    if not club or club.archived or (info and info.status!='approved') or (org and org.status!='approved'):raise HTTPException(404,'Программа недоступна')
    return club,info
@router.get('/market/programs')
def market(age:int|None=None,city:str='',max_price:int|None=None,format:str='',schedule:str='',interest:str='',user=Depends(parent),db=Depends(get_db)):
    if age is not None and not 1<=age<=17:raise HTTPException(422,'Возраст должен быть от 1 до 17 лет')
    if max_price is not None and not 0<=max_price<=1000000:raise HTTPException(422,'Проверьте бюджет')
    if format not in ('','online','offline','hybrid') or len(city)>80 or len(schedule)>300 or len(interest)>40:raise HTTPException(422,'Проверьте фильтры')
    clubs=db.scalars(select(Club).where(Club.archived==False).order_by(Club.name));items=[]
    for c in clubs:
        try:club,info=public_program(db,c.id)
        except HTTPException:continue
        if age is not None and not c.min_age<=age<=c.max_age:continue
        if city and c.city.casefold()!=city.strip().casefold():continue
        if max_price is not None and (not info or info.price_rub>max_price):continue
        if format and (not info or info.format!=format):continue
        if schedule and (not info or schedule.casefold() not in info.schedule.casefold()):continue
        if interest and (not info or interest.casefold() not in [t.casefold() for t in info.tags]):continue
        items.append(program_data(db,c))
    return items
@router.get('/market/programs/{id}')
def market_detail(id:str,user=Depends(parent),db=Depends(get_db)):
    club,info=public_program(db,id)
    slots=db.scalars(select(TrialSlot).where(TrialSlot.club_id==id,TrialSlot.enabled==True,TrialSlot.starts_at>now()).order_by(TrialSlot.starts_at))
    reviews=db.scalars(select(Review).where(Review.club_id==id,Review.status=='published').order_by(Review.created_at.desc())).all()
    return {**program_data(db,club),'slots':[data(s,'id starts_at capacity') for s in slots],
            'reviews':[data(r,'id rating message created_at') for r in reviews],'rating':round(sum(r.rating for r in reviews)/len(reviews),1) if reviews else None,
            'favorite':bool(db.get(Favorite,(user.id,id))),'organization':data(db.get(Organization,info.organization_id),'id name') if info and info.organization_id else None}
@router.get('/favorites')
def favorites(user=Depends(parent),db=Depends(get_db)):return [f.club_id for f in db.scalars(select(Favorite).where(Favorite.user_id==user.id))]
@router.put('/favorites/{id}')
def favorite(id:str,user=Depends(parent),db=Depends(get_db)):
    public_program(db,id)
    from sqlalchemy.dialects.postgresql import insert
    db.execute(insert(Favorite).values(user_id=user.id,club_id=id).on_conflict_do_nothing());db.commit();return {'ok':True}
@router.delete('/favorites/{id}')
def unfavorite(id:str,user=Depends(parent),db=Depends(get_db)):
    db.execute(delete(Favorite).where(Favorite.user_id==user.id,Favorite.club_id==id));db.commit();return {'ok':True}
class ReviewInput(Input):
    rating:int=Field(ge=1,le=5)
    message:str=Field(min_length=3,max_length=2000)
@router.post('/market/programs/{id}/reviews')
def write_review(id:str,body:ReviewInput,user=Depends(parent),db=Depends(get_db)):
    from .platform_services import sensitive_limit
    sensitive_limit(db,user,'review',10)
    public_program(db,id);db.scalar(select(User).where(User.id==user.id).with_for_update())
    if not db.scalar(select(Result.id).join(TestSession).join(Child).where(Child.owner_id==user.id).limit(1)):raise HTTPException(403,'Отзыв доступен после завершённого прохождения. Это не подтверждение посещения.')
    review=db.scalar(select(Review).where(Review.user_id==user.id,Review.club_id==id))
    if not review:review=Review(user_id=user.id,club_id=id,**body.model_dump());db.add(review)
    else:
        review.rating=body.rating;review.message=body.message;review.status='pending';review.reason=''
    db.commit();return data(review,'id status message rating')
@router.get('/admin/reviews')
def review_queue(user=Depends(admin),db=Depends(get_db)):return [data(r,'id club_id rating message status reason') for r in db.scalars(select(Review).order_by(Review.created_at.desc()))]
@router.post('/admin/reviews/{id}/decision')
def decide_review(id:str,body:Decision,user=Depends(admin),db=Depends(get_db)):
    review=db.get(Review,id)
    if not review:raise HTTPException(404)
    review.status='published' if body.approved else 'rejected';review.reason=body.reason;audit(db,user,'review.decision',id,review.status);db.commit();return {'ok':True}

class BookingInput(Input):
    child_id:str;slot_id:str;request_id:str=Field(pattern=r'^[a-f0-9-]{36}$')
    contact:str=Field(min_length=3,max_length=240)
    consent:bool
@router.post('/bookings')
def book(body:BookingInput,user=Depends(parent),db=Depends(get_db)):
    from .platform_services import sensitive_limit
    sensitive_limit(db,user,'booking',30)
    consent_required(db,user)
    if not body.consent:raise HTTPException(422,'Подтвердите передачу контакта организации')
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    old=db.scalar(select(Booking).where(Booking.parent_id==user.id,Booking.request_id==body.request_id))
    if old:
        if old.child_id!=body.child_id or old.slot_id!=body.slot_id:raise HTTPException(409,'Идентификатор уже использован')
        return booking_data(db,old)
    child=db.scalar(select(Child).where(Child.id==body.child_id,Child.owner_id==user.id))
    if not child:raise HTTPException(404)
    slot=db.scalar(select(TrialSlot).where(TrialSlot.id==body.slot_id).with_for_update())
    if not slot or not slot.enabled or slot.starts_at<=now():raise HTTPException(409,'Время недоступно')
    club,info=public_program(db,slot.club_id)
    if not info or not info.organization_id:raise HTTPException(409,'Программа пока не принимает заявки')
    if not club.min_age<=child.age<=club.max_age:raise HTTPException(422,'Возраст не соответствует программе')
    count=db.scalar(select(func.count()).select_from(Booking).where(Booking.slot_id==slot.id,Booking.status.in_(['new','accepted','completed','cancellation_requested'])))
    if count>=slot.capacity:raise HTTPException(409,'Свободных мест нет')
    duplicate=db.scalar(select(Booking).where(Booking.child_id==child.id,Booking.slot_id==slot.id,Booking.status.in_(['new','accepted','completed','cancellation_requested'])))
    if duplicate:return booking_data(db,duplicate)
    item=Booking(parent_id=user.id,child_id=child.id,club_id=club.id,slot_id=slot.id,contact=body.contact,request_id=body.request_id,snapshot={'name':child.name,'age':child.age})
    db.add(item);db.flush();db.add(BookingEvent(booking_id=item.id,actor_id=user.id,status='new'))
    org=db.get(Organization,info.organization_id)
    if org.owner_id:notify(db,org.owner_id,'booking','Новая заявка на пробное занятие',f'booking:{item.id}:new','/partner/bookings')
    db.commit();return booking_data(db,item)

def booking_data(db,b):
    club=db.get(Club,b.club_id);slot=db.get(TrialSlot,b.slot_id)
    return {**data(b,'id child_id club_id slot_id status contact snapshot note created_at'),'program_name':club.name,'starts_at':slot.starts_at,
            'history':[data(e,'id status note created_at') for e in db.scalars(select(BookingEvent).where(BookingEvent.booking_id==b.id).order_by(BookingEvent.created_at))]}
@router.get('/bookings')
def my_bookings(user=Depends(parent),db=Depends(get_db)):return [booking_data(db,b) for b in db.scalars(select(Booking).where(Booking.parent_id==user.id).order_by(Booking.created_at.desc()))]
@router.get('/partner/bookings')
def partner_bookings(user=Depends(current_user),db=Depends(get_db)):
    org=partner_org(db,user)
    return [booking_data(db,b) for b in db.scalars(select(Booking).join(ProgramInfo,ProgramInfo.club_id==Booking.club_id).where(ProgramInfo.organization_id==org.id).order_by(Booking.created_at.desc()))]
class BookingDecision(Input):
    status:Literal['accepted','rejected','completed','cancelled','cancellation_requested','ended']
    note:str=Field(default='',max_length=1000)
@router.post('/bookings/{id}/status')
def booking_status(id:str,body:BookingDecision,user=Depends(current_user),db=Depends(get_db)):
    item=db.scalar(select(Booking).where(Booking.id==id).with_for_update())
    if not item:raise HTTPException(404)
    if user.role=='parent':
        if item.parent_id!=user.id:raise HTTPException(404)
        transitions={'new':['cancelled'],'accepted':['cancellation_requested'],'completed':['cancellation_requested']}
    elif user.role=='partner':
        owns_program(db,user,item.club_id);transitions={'new':['accepted','rejected'],'accepted':['completed','rejected'],'cancellation_requested':['ended','accepted']}
    else:raise HTTPException(403)
    if item.status==body.status:return booking_data(db,item)
    if body.status not in transitions.get(item.status,[]):raise HTTPException(409,'Недопустимый переход статуса')
    item.status=body.status;item.note=body.note;db.add(BookingEvent(booking_id=id,actor_id=user.id,status=body.status,note=body.note))
    notify(db,item.parent_id,'booking','Статус заявки: '+{'accepted':'принята','rejected':'отклонена','completed':'пробное занятие завершено, запись активна','cancelled':'отменена','cancellation_requested':'запрошено прекращение занятий','ended':'занятия прекращены'}[body.status],f'booking:{id}:{uuid4()}','/bookings',item.child_id)
    if user.role=='parent':
        org=db.get(Organization,db.get(ProgramInfo,item.club_id).organization_id)
        if org.owner_id:notify(db,org.owner_id,'booking','Родитель изменил заявку',f'booking:{id}:{uuid4()}','/partner/bookings')
    audit(db,user,'booking.status',id,body.status);db.commit();return booking_data(db,item)
@router.get('/partner/bookings.csv')
def export_bookings(user=Depends(current_user),db=Depends(get_db)):
    records=partner_bookings(user,db);out=io.StringIO();writer=csv.writer(out,delimiter=';');writer.writerow(['Заявка','Программа','Ребёнок','Возраст','Контакт','Время','Статус'])
    def cell(v):
        s=str(v);return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s
    for b in records:writer.writerow([cell(v) for v in [b['id'],b['program_name'],b['snapshot']['name'],b['snapshot']['age'],b['contact'],b['starts_at'],b['status']]])
    return Response('\ufeff'+out.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="bookings.csv"'})

@router.get('/partner/stats')
def partner_stats(user=Depends(current_user),db=Depends(get_db)):
    org=partner_org(db,user)
    rows=db.execute(select(Booking.status,func.count()).join(ProgramInfo,ProgramInfo.club_id==Booking.club_id).where(ProgramInfo.organization_id==org.id).group_by(Booking.status)).all()
    return {'bookings_by_status':dict(rows),'total_bookings':sum(n for _,n in rows),'programs':db.scalar(select(func.count()).select_from(ProgramInfo).where(ProgramInfo.organization_id==org.id))}
