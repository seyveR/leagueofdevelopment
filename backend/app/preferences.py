from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field,model_validator
from sqlalchemy import String,ForeignKey,JSON,Integer,select
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy.dialects.postgresql import insert
from .db import Base,get_db
from .models import Child
from .security import current_user

class Preference(Base):
    __tablename__='preferences'
    id:Mapped[str]=mapped_column(String(80),primary_key=True)
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    child_id:Mapped[str|None]=mapped_column(ForeignKey('children.id',ondelete='CASCADE'),nullable=True,unique=True)
    schema_version:Mapped[int]=mapped_column(Integer,default=1)
    values:Mapped[dict]=mapped_column(JSON,default=dict)

class Settings(BaseModel):
    model_config=ConfigDict(extra='forbid')
    speech:bool=False
    autoplay:bool=False
    voice:Literal['ru-sofia','ru-lev']='ru-sofia'
    volume:float=Field(default=.8,ge=0,le=1)
    rate:float=Field(default=1,ge=.8,le=1.2)
    character:bool=True
    reduced_motion:bool=False
    text_size:Literal['normal','large']='normal'
    notify_bookings:bool=True
    notify_retest:bool=True
    notify_subscription:bool=True
    instruction_format:Literal['text','audio']='text'
    @model_validator(mode='after')
    def sound_dependencies(self):
        if not self.speech:self.autoplay=False
        return self

DEFAULTS=Settings().model_dump()
router=APIRouter(prefix='/api/settings',tags=['Настройки'])

def scope(db,user,child_id=None):
    if child_id:
        child=db.scalar(select(Child).where(Child.id==child_id,Child.owner_id==user.id))
        if not child:raise HTTPException(404,'Ребёнок не найден')
    return f'child:{child_id}' if child_id else f'user:{user.id}'

def effective(db,user_id,child_id=None):
    parent=db.get(Preference,f'user:{user_id}')
    child=db.get(Preference,f'child:{child_id}') if child_id else None
    return Settings(**{**DEFAULTS,**(parent.values if parent else {}),**(child.values if child else {})}).model_dump()

@router.get('')
def read(child_id:str|None=None,user=Depends(current_user),db=Depends(get_db)):
    key=scope(db,user,child_id)
    return {'schema_version':1,'settings':effective(db,user.id,child_id),'overridden':bool(child_id and db.get(Preference,key)),
            'notification_channels':{'in_app':True,'email':False,'sms':False,'push':False}}

@router.put('')
def save(body:Settings,child_id:str|None=None,user=Depends(current_user),db=Depends(get_db)):
    key=scope(db,user,child_id)
    db.execute(insert(Preference).values(id=key,user_id=user.id,child_id=child_id,schema_version=1,values=body.model_dump()).on_conflict_do_update(index_elements=['id'],set_={'values':body.model_dump(),'schema_version':1}))
    db.commit()
    return read(child_id,user,db)

@router.delete('')
def inherit(child_id:str,user=Depends(current_user),db=Depends(get_db)):
    key=scope(db,user,child_id);row=db.get(Preference,key)
    if row:db.delete(row)
    db.commit();return read(child_id,user,db)
