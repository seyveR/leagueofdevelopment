from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select,func
from .db import get_db
from .models import User,Child,TestSession,Result,Answer,TaskSet,Event,Club
from .outputs import Output,SessionOut,ResultOut
from .security import admin

router=APIRouter(prefix='/api/admin',dependencies=[Depends(admin)])

class ParentOut(Output):
    id:str;email:str

class CompletionOut(Output):
    session:SessionOut;parent:ParentOut;result:ResultOut

class CompletionsOut(Output):
    items:list[CompletionOut];total:int;offset:int;limit:int

class AnswerOut(Output):
    task_id:str;category:str;prompt:str;stimulus:str;selected:str|None;correct:str;is_correct:bool;answered_at:datetime|None

class CompletionDetailOut(CompletionOut):
    task_set_version:str;answers:list[AnswerOut]

class ClubTransitionsOut(Output):
    club_id:str;name:str;city:str;archived:bool;count:int;last_opened_at:datetime

class TransitionsOut(Output):
    items:list[ClubTransitionsOut];total:int;total_openings:int;offset:int;limit:int

def completed_query():
    return select(TestSession,User,Result).join(Child,Child.id==TestSession.child_id).join(User,User.id==Child.owner_id).join(Result,Result.session_id==TestSession.id).where(TestSession.status=='completed')

@router.get('/completions',response_model=CompletionsOut)
def completions(offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),db=Depends(get_db)):
    query=completed_query()
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.execute(query.order_by(TestSession.completed_at.desc(),TestSession.id).offset(offset).limit(limit)).all()
    return {'items':[{'session':s,'parent':u,'result':r} for s,u,r in rows],'total':total,'offset':offset,'limit':limit}

@router.get('/completions/{id}',response_model=CompletionDetailOut)
def completion(id:str,db=Depends(get_db)):
    row=db.execute(completed_query().where(TestSession.id==id)).first()
    if not row:raise HTTPException(404,'Завершённое прохождение не найдено')
    session,parent,result=row
    task_set=db.get(TaskSet,session.task_set_id)
    answers={a.task_id:a for a in db.scalars(select(Answer).where(Answer.session_id==id)).all()}
    details=[]
    from .adaptive import tasks_for
    for task in tasks_for(db,session):
        answer=answers.get(task['id']);labels={o['id']:o['label'] for o in task['options']}
        details.append({'task_id':task['id'],'category':task['category'],'prompt':task['prompt'],'stimulus':task['stimulus'],
                        'selected':labels.get(answer.option_id) if answer else None,'correct':labels[task['correct']],
                        'is_correct':bool(answer and answer.option_id==task['correct']),'answered_at':answer.created_at if answer else None})
    return {'session':session,'parent':parent,'result':result,'task_set_version':task_set.version,'answers':details}

@router.get('/club-transitions',response_model=TransitionsOut)
def transitions(offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),db=Depends(get_db)):
    grouped=select(Event.club_id,func.count().label('count'),func.max(Event.created_at).label('last_opened_at')).where(Event.kind=='club_open').group_by(Event.club_id).subquery()
    query=select(Club,grouped.c.count,grouped.c.last_opened_at).join(grouped,grouped.c.club_id==Club.id)
    total=db.scalar(select(func.count()).select_from(grouped))
    openings=db.scalar(select(func.count()).select_from(Event).where(Event.kind=='club_open'))
    rows=db.execute(query.order_by(grouped.c.count.desc(),Club.name,Club.id).offset(offset).limit(limit)).all()
    return {'items':[{'club_id':c.id,'name':c.name,'city':c.city,'archived':c.archived,'count':n,'last_opened_at':last} for c,n,last in rows],
            'total':total,'total_openings':openings,'offset':offset,'limit':limit}
