import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select, func, text, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .db import get_db
from .models import User,AuthSession,Child,TaskSet,TestSession,Answer,Result,Club,Rule,Feedback,Event,now
from .schemas import Credentials,PasswordChange,ChildInput,StartInput,AnswerInput,PhaseInput,FeedbackInput,OpenInput,ClubInput,RuleInput
from .outputs import AuthOut,ChildOut,SessionOut,StateOut,DetailOut,ResultOut,ClubOut,RuleOut,RecommendationOut,FeedbackOut
from .security import current_user,parent,admin,csrf_guard,login_session,hasher,verify,throttle,cookie,digest,COOKIE,CSRF,dummy_hash,reset_login_failures,reject_login
from . import assessment
from .admin_reports import router as admin_reports_router

CONSENT_VERSION='local-2026-10-22-v1'
CONSENT_TEXT='Я как родитель или законный представитель разрешаю сохранять введённые данные ребёнка, ответы и результаты в локальной базе приложения для проверки его функций. Данные доступны моей учётной записи и не передаются кружкам. Текст предназначен для локального прототипа и требует юридической проверки перед реальным использованием.'
app=FastAPI(title='Лига развития API',version='0.2.1',docs_url='/api/docs',openapi_url='/api/openapi.json',redoc_url=None,dependencies=[Depends(csrf_guard)])

@app.exception_handler(RequestValidationError)
def validation_failure(request,exc):
    # Pydantic's default input echo can include a rejected password. Never return it.
    return JSONResponse(status_code=422,content={'detail':'Проверьте введённые данные.','fields':['.'.join(str(p) for p in error['loc']) for error in exc.errors()]})

@app.exception_handler(IntegrityError)
def conflict(request,exc): return JSONResponse(status_code=409,content={'detail':'Запись уже существует или её состояние изменилось. Обновите страницу.'})
@app.exception_handler(SQLAlchemyError)
def storage_failure(request,exc): return JSONResponse(status_code=503,content={'detail':'Не удалось сохранить данные. Повторите действие.'})
@app.middleware('http')
async def response_headers(request,call_next):
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response

def owned_child(db,id,user,lock=False):
    query=select(Child).where(Child.id==id,Child.owner_id==user.id)
    child=db.scalar(query.with_for_update() if lock else query)
    if not child: raise HTTPException(404,'Профиль не найден')
    return child

def owned_session(db,id,user,lock=False):
    query=select(TestSession).join(Child).where(TestSession.id==id,Child.owner_id==user.id)
    s=db.scalar(query.with_for_update(of=TestSession) if lock else query)
    if not s: raise HTTPException(404,'Прохождение не найдено')
    return s

@app.get('/api/health')
def health(db=Depends(get_db)):
    db.execute(text('SELECT 1'));return {'status':'ok'}

@app.get('/api/consent')
def consent(): return {'version':CONSENT_VERSION,'text':CONSENT_TEXT}

@app.get('/api/auth/session',response_model=AuthOut)
def auth_session(request:Request,response:Response,db=Depends(get_db)):
    csrf=request.cookies.get(CSRF) or secrets.token_urlsafe(32)
    cookie(response,CSRF,csrf,604800)
    try: user=current_user(request,db)
    except HTTPException: user=None
    return {'user':user,'csrf':csrf}

@app.post('/api/auth/register',response_model=AuthOut)
def register(body:Credentials,request:Request,response:Response,db=Depends(get_db)):
    email=str(body.email).lower(); throttle(db,request.client.host,email)
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,'Этот email уже зарегистрирован')
    user=User(email=email,password_hash=hasher.hash(body.password),role='parent')
    db.add(user);db.flush();return login_session(db,user,response)

@app.post('/api/auth/login',response_model=AuthOut)
def login(body:Credentials,request:Request,response:Response,db=Depends(get_db)):
    email=str(body.email).lower()
    user=db.scalar(select(User).where(User.email==email).with_for_update())
    valid=verify(user.password_hash if user else dummy_hash,body.password)
    if not user or not valid:reject_login(db,email)
    reset_login_failures(db,email)
    return login_session(db,user,response)

@app.post('/api/auth/logout')
def logout(request:Request,response:Response,db=Depends(get_db)):
    token=request.cookies.get(COOKIE)
    if token:db.execute(delete(AuthSession).where(AuthSession.token_hash==digest(token)))
    db.commit();response.delete_cookie(COOKIE,path='/');response.delete_cookie(CSRF,path='/');return {'ok':True}

@app.post('/api/auth/password')
def change_password(body:PasswordChange,request:Request,response:Response,user=Depends(current_user),db=Depends(get_db)):
    throttle(db,request.client.host,f'password-change:{user.id}')
    # Serialize with login and other password changes, reading the current hash.
    user=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
    if not verify(user.password_hash,body.current_password):raise HTTPException(400,'Текущий пароль указан неверно')
    if body.current_password==body.new_password:raise HTTPException(400,'Новый пароль должен отличаться от текущего')
    user.password_hash=hasher.hash(body.new_password)
    db.execute(delete(AuthSession).where(AuthSession.user_id==user.id))
    db.commit()
    response.delete_cookie(COOKIE,path='/');response.delete_cookie(CSRF,path='/')
    return {'ok':True}

@app.get('/api/state',response_model=StateOut)
def state(user=Depends(parent),db=Depends(get_db)):
    children=db.scalars(select(Child).where(Child.owner_id==user.id).order_by(Child.created_at)).all()
    sessions=db.scalars(select(TestSession).join(Child).where(Child.owner_id==user.id).order_by(TestSession.created_at.desc())).all()
    results=db.scalars(select(Result).join(TestSession).join(Child).where(Child.owner_id==user.id)).all()
    return {'children':children,'sessions':sessions,'results':results}

@app.get('/api/children/{id}',response_model=ChildOut)
def child_get(id:str,user=Depends(parent),db=Depends(get_db)): return owned_child(db,id,user)

@app.post('/api/children',response_model=ChildOut)
def child_create(body:ChildInput,user=Depends(parent),db=Depends(get_db)):
    if not body.consent or body.consent_version!=CONSENT_VERSION: raise HTTPException(422,'Подтвердите актуальное согласие на обработку данных ребёнка')
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    if body.request_id:
        old=db.get(Child,body.request_id)
        if old:
            if old.owner_id!=user.id:raise HTTPException(409,'Идентификатор запроса уже использован')
            return old
    child=Child(**({'id':body.request_id} if body.request_id else {}),owner_id=user.id,**body.model_dump(exclude={'consent','consent_version','request_id'}),consent_at=now(),consent_version=CONSENT_VERSION)
    db.add(child);db.commit();return child

@app.put('/api/children/{id}',response_model=ChildOut)
def child_update(id:str,body:ChildInput,user=Depends(parent),db=Depends(get_db)):
    child=owned_child(db,id,user,True)
    for k,v in body.model_dump(exclude={'consent','consent_version','request_id'}).items(): setattr(child,k,v)
    db.commit();return child

@app.post('/api/sessions',response_model=SessionOut)
def start(body:StartInput,user=Depends(parent),db=Depends(get_db)):
    child=owned_child(db,body.child_id,user,True)
    # Row-lock on child serializes starts, including concurrent retries.
    old=db.scalar(select(TestSession).where(TestSession.child_id==child.id,TestSession.status=='in_progress'))
    if old: return old
    existing=db.get(TestSession,body.request_id)
    if existing:
        if existing.child_id!=child.id: raise HTTPException(409,'Повторный идентификатор запроса')
        return existing
    if not 7<=child.age<=9: raise HTTPException(422,'Набор доступен детям 7–9 лет')
    taskset=db.scalar(select(TaskSet).where(TaskSet.active==True).order_by(TaskSet.created_at.desc()))
    if not taskset: raise HTTPException(503,'Набор заданий недоступен')
    s=TestSession(id=body.request_id,child_id=child.id,task_set_id=taskset.id,child_snapshot={'name':child.name,'age':child.age,'city':child.city,'gender':child.gender,'interests':child.interests},algorithm_version=assessment.VERSION)
    db.add(s);db.commit();return s

@app.get('/api/sessions/{id}',response_model=DetailOut)
def session_detail(id:str,user=Depends(parent),db=Depends(get_db)):
    s=owned_session(db,id,user);tasks=db.get(TaskSet,s.task_set_id).tasks
    task=None
    if s.position<len(tasks) and s.status=='in_progress':
        t=tasks[s.position]; memory=t['category']=='memory'
        task={'id':t['id'],'category':t['category'],'prompt':t['prompt'],'stimulus':t['stimulus'] if not memory or s.phase=='view' else None,'options':[] if memory and s.phase=='view' else t['options']}
    answers=db.scalars(select(Answer).where(Answer.session_id==id)).all()
    return {'session':s,'task':task,'answers':[{'task_id':a.task_id,'option_id':a.option_id} for a in answers],'total':len(tasks)}

@app.post('/api/sessions/{id}/hide',response_model=SessionOut)
def hide(id:str,body:PhaseInput,user=Depends(parent),db=Depends(get_db)):
    s=owned_session(db,id,user,True);tasks=db.get(TaskSet,s.task_set_id).tasks
    if s.status!='in_progress' or s.position>=len(tasks): raise HTTPException(409,'Шаг уже завершён')
    t=tasks[s.position]
    if t['id']!=body.task_id or t['category']!='memory': raise HTTPException(422,'Этап запоминания недоступен')
    s.phase='answer';db.commit();return s

@app.post('/api/sessions/{id}/answers',response_model=SessionOut)
def save_answer(id:str,body:AnswerInput,user=Depends(parent),db=Depends(get_db)):
    s=owned_session(db,id,user,True);tasks=db.get(TaskSet,s.task_set_id).tasks
    previous=db.scalar(select(Answer).where(Answer.session_id==id,Answer.task_id==body.task_id))
    if previous:
        if previous.option_id==body.option_id: return s
        raise HTTPException(409,'Сохранённый ответ нельзя изменить')
    if s.status!='in_progress' or s.position>=len(tasks): raise HTTPException(409,'Прохождение завершено')
    t=tasks[s.position]
    if t['id']!=body.task_id or body.option_id not in [o['id'] for o in t['options']]: raise HTTPException(422,'Недопустимый ответ или порядок заданий')
    if t['category']=='memory' and s.phase!='answer': raise HTTPException(409,'Сначала скройте материал для запоминания')
    db.add(Answer(session_id=id,task_id=t['id'],option_id=body.option_id));s.position+=1;s.phase='view';db.commit();return s

@app.post('/api/sessions/{id}/complete',response_model=ResultOut)
def complete(id:str,user=Depends(parent),db=Depends(get_db)):
    s=owned_session(db,id,user,True)
    previous=db.scalar(select(Result).where(Result.session_id==id))
    if previous:return previous
    tasks=db.get(TaskSet,s.task_set_id).tasks;answers={a.task_id:a.option_id for a in db.scalars(select(Answer).where(Answer.session_id==id)).all()}
    if s.position!=len(tasks) or set(answers)!={t['id'] for t in tasks}: raise HTTPException(409,'Ответьте на все обязательные задания')
    if s.algorithm_version!=assessment.VERSION: raise HTTPException(409,'Нужна сохранённая версия алгоритма')
    r=Result(session_id=id,algorithm_version=s.algorithm_version,scores=assessment.evaluate(tasks,answers));db.add(r)
    s.status='completed';s.completed_at=now()
    db.add(Event(user_id=user.id,session_id=id,kind='completed',request_id=f'completed:{id}'))
    db.commit();return r

@app.get('/api/sessions/{id}/result',response_model=ResultOut)
def result_get(id:str,user=Depends(parent),db=Depends(get_db)):
    owned_session(db,id,user);r=db.scalar(select(Result).where(Result.session_id==id))
    if not r:raise HTTPException(409,'Прохождение ещё не завершено')
    return r

def recommendations(db,s):
    r=db.scalar(select(Result).where(Result.session_id==s.id))
    if not r:raise HTTPException(409,'Сначала завершите тест')
    age=s.child_snapshot['age'];city=s.child_snapshot['city'].strip().casefold()
    rows=db.execute(select(Club,Rule).join(Rule).where(Club.archived==False,Club.min_age<=age,Club.max_age>=age).order_by(Rule.priority.desc(),Club.id)).all()
    return [{'club':club,'explanation':rule.explanation,'rules_version':'rules-1.0.0'} for club,rule in rows if club.city.strip().casefold()==city and (rule.metric=='any' or rule.minimum<=r.scores[rule.metric]['percent']<=rule.maximum)][:5]

@app.get('/api/sessions/{id}/recommendations',response_model=list[RecommendationOut])
def recommend(id:str,user=Depends(parent),db=Depends(get_db)): return recommendations(db,owned_session(db,id,user))

@app.get('/api/clubs',response_model=list[ClubOut])
def catalog(age:int | None=None,city:str | None=None,user=Depends(parent),db=Depends(get_db)):
    q=select(Club).where(Club.archived==False)
    if age is not None:q=q.where(Club.min_age<=age,Club.max_age>=age)
    if city:q=q.where(func.lower(Club.city)==city.strip().lower())
    return db.scalars(q.order_by(Club.name)).all()

@app.get('/api/clubs/{id}',response_model=ClubOut)
def club_get(id:str,user=Depends(parent),db=Depends(get_db)):
    club=db.get(Club,id)
    if not club or club.archived:raise HTTPException(404,'Кружок недоступен')
    return club

@app.post('/api/sessions/{id}/club-open')
def club_open(id:str,body:OpenInput,user=Depends(parent),db=Depends(get_db)):
    s=owned_session(db,id,user,True)
    old=db.scalar(select(Event).where(Event.user_id==user.id,Event.request_id==body.request_id))
    if old:
        if old.session_id!=id or old.club_id!=body.club_id:raise HTTPException(409,'Идентификатор события уже использован')
        return {'ok':True}
    if body.club_id not in [r['club'].id for r in recommendations(db,s)]: raise HTTPException(422,'Кружок отсутствует в рекомендациях')
    db.add(Event(user_id=user.id,session_id=id,club_id=body.club_id,kind='club_open',request_id=body.request_id));db.commit();return {'ok':True}

@app.post('/api/feedback',response_model=FeedbackOut)
def feedback(body:FeedbackInput,user=Depends(parent),db=Depends(get_db)):
    # Lock user to serialize duplicate requests from separate sessions.
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    old=db.scalar(select(Feedback).where(Feedback.user_id==user.id,Feedback.request_id==body.request_id))
    if old:return old
    item=Feedback(user_id=user.id,**body.model_dump());db.add(item);db.commit();return item

@app.get('/api/admin/clubs',response_model=list[ClubOut])
def admin_clubs(user=Depends(admin),db=Depends(get_db)): return db.scalars(select(Club).order_by(Club.created_at)).all()
@app.post('/api/admin/clubs',response_model=ClubOut)
def add_club(body:ClubInput,user=Depends(admin),db=Depends(get_db)):
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    if body.request_id:
        old=db.get(Club,body.request_id)
        if old:return old
    club=Club(**({'id':body.request_id} if body.request_id else {}),**body.model_dump(exclude={'request_id'}));db.add(club);db.flush();db.add(Rule(club_id=club.id,explanation='Занятия по программе кружка.',metric='any'));db.commit();return club
@app.put('/api/admin/clubs/{id}',response_model=ClubOut)
def edit_club(id:str,body:ClubInput,user=Depends(admin),db=Depends(get_db)):
    club=db.get(Club,id)
    if not club:raise HTTPException(404,'Кружок не найден')
    for k,v in body.model_dump(exclude={'request_id'}).items():setattr(club,k,v)
    db.commit();return club
@app.get('/api/admin/rules',response_model=list[RuleOut])
def rules(user=Depends(admin),db=Depends(get_db)):return db.scalars(select(Rule)).all()
@app.put('/api/admin/clubs/{id}/rule',response_model=RuleOut)
def edit_rule(id:str,body:RuleInput,user=Depends(admin),db=Depends(get_db)):
    rule=db.scalar(select(Rule).where(Rule.club_id==id).with_for_update())
    if not rule:raise HTTPException(404,'Кружок не найден')
    for k,v in body.model_dump().items():setattr(rule,k,v)
    db.commit();return rule
@app.get('/api/admin/stats')
def stats(user=Depends(admin),db=Depends(get_db)):
    return {'completed':db.scalar(select(func.count()).select_from(Event).where(Event.kind=='completed')),'club_open':db.scalar(select(func.count()).select_from(Event).where(Event.kind=='club_open'))}
@app.get('/api/admin/feedback',response_model=list[FeedbackOut])
def all_feedback(user=Depends(admin),db=Depends(get_db)):return db.scalars(select(Feedback).order_by(Feedback.created_at.desc())).all()

app.include_router(admin_reports_router)

