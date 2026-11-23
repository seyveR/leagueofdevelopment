from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import Field
from sqlalchemy import String,JSON,select
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base,get_db
from .models import Child,Club,Rule,TestSession,Result
from .schemas import Input
from .security import parent,admin
from .marketplace import public_program
from .platform_services import audit

class RecommendationConfig(Base):
    __tablename__='recommendation_config'
    id:Mapped[str]=mapped_column(String(40),primary_key=True)
    weights:Mapped[dict]=mapped_column(JSON)

class Weights(Input):
    interests:int=Field(default=30,ge=0,le=100)
    result:int=Field(default=15,ge=0,le=100)
    format:int=Field(default=10,ge=0,le=100)
    budget:int=Field(default=10,ge=0,le=100)
    schedule:int=Field(default=10,ge=0,le=100)
router=APIRouter(prefix='/api',tags=['Правила подбора'])
@router.get('/admin/recommendation-weights')
def weights(user=Depends(admin),db=Depends(get_db)):
    row=db.get(RecommendationConfig,'weighted-1');return row.weights if row else Weights().model_dump()
@router.put('/admin/recommendation-weights')
def save_weights(body:Weights,user=Depends(admin),db=Depends(get_db)):
    row=db.get(RecommendationConfig,'weighted-1')
    if not row:row=RecommendationConfig(id='weighted-1',weights=body.model_dump());db.add(row)
    else:row.weights=body.model_dump()
    audit(db,user,'recommendations.weights','weighted-1');db.commit();return row.weights
@router.get('/market/recommendations/{id}')
def recommendations(id:str,format:str='',max_price:int|None=Query(None,ge=0,le=1000000),schedule:str='',user=Depends(parent),db=Depends(get_db)):
    session=db.scalar(select(TestSession).join(Child).where(TestSession.id==id,Child.owner_id==user.id))
    if not session:raise HTTPException(404)
    result=db.scalar(select(Result).where(Result.session_id==id))
    if not result:raise HTTPException(409,'Сначала завершите задания')
    config=db.get(RecommendationConfig,'weighted-1');w=config.weights if config else Weights().model_dump();items=[]
    snapshot=session.child_snapshot;interests={s.casefold() for s in snapshot.get('interests',[])}
    for c,rule in db.execute(select(Club,Rule).join(Rule).where(Club.archived==False,Club.min_age<=snapshot['age'],Club.max_age>=snapshot['age'])):
        if c.city.casefold()!=snapshot['city'].strip().casefold():continue
        try:club,info=public_program(db,c.id)
        except HTTPException:continue
        if session.algorithm_version.startswith('discovery-') and info and 'direction:consultation' in info.tags:continue
        if session.algorithm_version=='discovery-2.0.0':
            allowed=result.scores.get('recommended_codes',[])
            if not info or not any('direction:'+d in info.tags for d in allowed):continue
        if format and (not info or info.format!=format):continue
        if max_price is not None and (not info or info.price_rub>max_price):continue
        if schedule and (not info or schedule.casefold() not in info.schedule.casefold()):continue
        points=rule.priority;reasons=['Возраст и город соответствуют профилю на момент прохождения.']
        if info and interests.intersection(t.casefold() for t in info.tags):points+=w['interests'];reasons.append('Совпадают указанные интересы.')
        group=result.scores.get(rule.metric)
        if session.algorithm_version=='discovery-2.0.0':
            directions=[d for d in result.scores.get('recommended_codes',[]) if info and 'direction:'+d in info.tags]
            direction=max(directions,key=lambda d:result.scores['affinities'][d])
            points+=w['result']*result.scores['affinities'][direction]/100
            primary={d['code'] for d in result.scores.get('directions',[])}
            if direction in primary:points+=1000
            reasons.append('Основное направление по результатам заданий.' if direction in primary else 'Выбран интерес к творческим занятиям.' if not primary else 'Дополнительное направление, прошедшее порог подбора.')
        elif session.algorithm_version=='discovery-1.0.0':
            from .journey_assessment import reason
            from .journey_content import DIRECTIONS
            directions=[t.removeprefix('direction:') for t in (info.tags if info else []) if t.startswith('direction:')]
            direction=max((d for d in directions if d in DIRECTIONS),key=lambda d:result.scores['affinities'].get(d,0),default=None)
            if direction:
                points+=w['result']*result.scores['affinities'].get(direction,0)/10
                reasons.append(reason(direction,{k:result.scores[k] for k in ('logic','attention','memory','spatial','story') if k in result.scores},result.scores.get('preferences',{})))
        elif group and rule.minimum<=group['percent']<=rule.maximum:points+=w['result'];reasons.append('Совпало предварительное правило каталога для этого набора заданий.')
        for active,key,label in [(bool(format),'format','Выбранный формат.'),(max_price is not None,'budget','В пределах выбранного бюджета.'),(bool(schedule),'schedule','Совпало расписание.')]:
            if active:points+=w[key];reasons.append(label)
        items.append({'club':c,'explanation':' '.join(reasons),'rules_version':'discovery-match-2.0.0' if session.algorithm_version=='discovery-2.0.0' else 'discovery-match-1.0.0' if session.algorithm_version=='discovery-1.0.0' else 'weighted-1.0.0','score':points})
    return sorted(items,key=lambda item:(-item['score'],item['club'].id))[:5]
