"""Independent original short sets. Existing task sets and answers remain immutable."""
from uuid import uuid5,NAMESPACE_URL
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from .db import get_db
from .models import Child,TaskSet,TestSession
from .schemas import Input
from .security import parent
from .age_tasks import SCENARIOS,group_for
from .platform_services import consent_required
from .preferences import effective
from .outputs import SessionOut
from pydantic import Field

from .domain_content import VERSION,NAMES,DESCRIPTIONS,SETS

def seed_sets(db):
    for spec in SETS.values():
        if not db.get(TaskSet,spec['id']):db.add(TaskSet(**spec,active=True))

def evaluate(tasks,answers,code):
    total=len(tasks);scored=code!='imagination'
    count=sum(answers.get(t['id'])==t['correct'] for t in tasks) if scored else 0
    scores={'completed':len(answers),'total':total,'correct':count,'test_code':code,'test_name':NAMES[code],'scored':scored,
            'comment':'Доля верных ответов только в этом ознакомительном наборе. Возрастных норм и оценки способностей нет.' if scored else 'Ответы сохранены. У творческих продолжений нет правильного варианта; талант и воображение не оцениваются баллом.'}
    if scored:scores[code]={'correct':count,'total':total,'percent':round(count/total*100,1)}
    return scores

router=APIRouter(prefix='/api/domain-tests',tags=['Отдельные тесты'])
@router.get('')
def catalog(child_id:str,user=Depends(parent),db=Depends(get_db)):
    child=db.scalar(select(Child).where(Child.id==child_id,Child.owner_id==user.id))
    if not child:raise HTTPException(404)
    group=group_for(child.age)
    return [{'code':c,'name':name,'description':DESCRIPTIONS[c],'duration':'3–5 минут','count':6,'set_id':SETS[(f"{group['min_age']}-{group['max_age']}",c)]['id'] if group else None,'available':bool(group)} for c,name in NAMES.items()]

class Start(Input):
    child_id:str
    request_id:str=Field(pattern=r'^[a-f0-9-]{36}$')
@router.post('/{code}/start',response_model=SessionOut)
def start(code:str,body:Start,user=Depends(parent),db=Depends(get_db)):
    child=db.scalar(select(Child).where(Child.id==body.child_id,Child.owner_id==user.id).with_for_update())
    if not child:raise HTTPException(404)
    consent_required(db,user);group=group_for(child.age)
    if code not in NAMES or not group:raise HTTPException(422,'Выберите доступный тест для возраста 3–17 лет')
    spec=SETS[(f"{group['min_age']}-{group['max_age']}",code)];taskset=db.get(TaskSet,spec['id'])
    if not taskset or not taskset.active:raise HTTPException(409,'Набор временно недоступен')
    existing=db.get(TestSession,body.request_id)
    if existing:
        if existing.child_id!=child.id or existing.task_set_id!=taskset.id:raise HTTPException(409,'Идентификатор уже использован')
        return existing
    old=db.scalar(select(TestSession).where(TestSession.child_id==child.id,TestSession.task_set_id==taskset.id,TestSession.status=='in_progress'))
    if old:return old
    session=TestSession(id=body.request_id,child_id=child.id,task_set_id=taskset.id,child_snapshot={'name':child.name,'age':child.age,'city':child.city,'gender':child.gender,'interests':child.interests},algorithm_version=VERSION,conditions=effective(db,user.id,child.id))
    db.add(session);db.commit();return session

