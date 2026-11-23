"""Parent-owned interactive journey; raw answers and derived results stay separate."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from .db import get_db
from .models import Child, TaskSet, TestSession, Answer
from .outputs import SessionOut
from .schemas import Input
from .security import parent
from .platform_services import consent_required
from .journey_content import GROUPS, SETS as LEGACY_SETS, group_for, public_task
from .discovery_v2 import VERSION,SETS
from .journey_assessment import validate

router=APIRouter(prefix='/api/journey',tags=['Возрастной путь'])

def seed_sets(db):
    for spec in [*LEGACY_SETS.values(),*SETS.values()]:
        if not db.get(TaskSet,spec['id']):db.add(TaskSet(**spec,active=True))

def owned(db,id,user,lock=False):
    query=select(TestSession).join(Child).where(TestSession.id==id,Child.owner_id==user.id)
    if lock:query=query.with_for_update(of=TestSession)
    session=db.scalar(query)
    if not session or session.algorithm_version not in ('discovery-1.0.0',VERSION):raise HTTPException(404,'Прохождение не найдено')
    return session

@router.get('')
def catalog(child_id:str,user=Depends(parent),db=Depends(get_db)):
    child=db.scalar(select(Child).where(Child.id==child_id,Child.owner_id==user.id))
    if not child:raise HTTPException(404)
    group=group_for(child.age)
    return {'available':bool(group),'groups':[{'min':a,'max':b} for a,b in GROUPS],
            'age_group':f'{group[0]}–{group[1]}' if group else None,
            'set_id':SETS[f'{group[0]}-{group[1]}']['id'] if group else None,
            'count':len(SETS[f'{group[0]}-{group[1]}']['tasks']) if group else 0,'version':VERSION}

class Start(Input):
    child_id:str
    request_id:str=Field(pattern=r'^[a-f0-9-]{36}$')

@router.post('/start',response_model=SessionOut)
def start(body:Start,user=Depends(parent),db=Depends(get_db)):
    child=db.scalar(select(Child).where(Child.id==body.child_id,Child.owner_id==user.id).with_for_update())
    if not child:raise HTTPException(404)
    consent_required(db,user)
    group=group_for(child.age)
    if not group:raise HTTPException(422,'Новый путь доступен с 4 до 17 лет')
    spec=SETS[f'{group[0]}-{group[1]}'];taskset=db.get(TaskSet,spec['id'])
    if not taskset or not taskset.active:raise HTTPException(409,'Набор временно недоступен')
    old=db.get(TestSession,body.request_id)
    if old:
        if old.child_id!=child.id or old.task_set_id!=taskset.id:raise HTTPException(409,'Идентификатор уже использован')
        return old
    old=db.scalar(select(TestSession).where(TestSession.child_id==child.id,TestSession.task_set_id==taskset.id,TestSession.status=='in_progress'))
    if old:return old
    session=TestSession(id=body.request_id,child_id=child.id,task_set_id=taskset.id,
        algorithm_version=VERSION,child_snapshot={k:getattr(child,k) for k in ('name','age','city','gender','interests')},
        conditions={'speech':False,'autoplay':False,'memory_mode':'visual','age_group':f'{group[0]}-{group[1]}'})
    db.add(session);db.commit();return session

@router.get('/{id}')
def detail(id:str,user=Depends(parent),db=Depends(get_db)):
    s=owned(db,id,user);tasks=db.get(TaskSet,s.task_set_id).tasks
    task=tasks[s.position] if s.position<len(tasks) and s.status=='in_progress' else None
    return {'session':SessionOut.model_validate(s),'total':len(tasks),'task':public_task(task,s.phase) if task else None}

class Response(Input):
    task_id:str=Field(max_length=40)
    payload:dict

@router.post('/{id}/answers',response_model=SessionOut)
def answer(id:str,body:Response,user=Depends(parent),db=Depends(get_db)):
    s=owned(db,id,user,True)
    old=db.scalar(select(Answer).where(Answer.session_id==id,Answer.task_id==body.task_id))
    if old:
        if old.payload==body.payload:return s
        raise HTTPException(409,'Ответ уже сохранён')
    tasks=db.get(TaskSet,s.task_set_id).tasks
    if s.status!='in_progress' or s.position>=len(tasks):raise HTTPException(409,'Прохождение завершено')
    task=tasks[s.position]
    if task['id']!=body.task_id:raise HTTPException(409,'Обновите текущий шаг')
    if task['mechanic']=='memory' and s.phase!='answer':raise HTTPException(409,'Сначала скройте картинки')
    validate(task,body.payload)
    db.add(Answer(session_id=id,task_id=task['id'],option_id='interactive',payload=body.payload))
    s.position+=1;s.phase='view';db.commit();return s
