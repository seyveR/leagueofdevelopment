from uuid import uuid5, NAMESPACE_DNS
from sqlalchemy import select,text
from .db import SessionLocal
from .models import TaskSet,Club,Rule
from .content import TASKS, SET_ID

def seed(db):
    db.execute(text('SELECT pg_advisory_xact_lock(704113)'))
    if not db.get(TaskSet,SET_ID):db.add(TaskSet(id=SET_ID,code='attention-memory-7-9',version='1.0.0',tasks=TASKS,active=True))
    catalog=[('Рисование','Рисование и работа с деталями.','any','Занятия с цветом, формой и деталями.'),('Конструирование','Сборка моделей по образцу.','attention','Работа по образцу и последовательным инструкциям.'),('Музыка','Ритмические упражнения и знакомство с инструментами.','memory','Повторение ритмов и музыкальных последовательностей.'),('Природа','Наблюдения за растениями и ведение дневника.','any','Наблюдение и описание окружающего мира.'),('Театр','Небольшие постановки и работа с текстом.','any','Работа с текстом, последовательностью действий и ролями.'),('Шахматы','Изучение правил и решение учебных задач.','any','Знакомство с правилами и планированием ходов.')]
    for i,(name,description,metric,explanation) in enumerate(catalog):
        id=str(uuid5(NAMESPACE_DNS,f'liga.seed.club.{i}'))
        if db.get(Club,id):continue
        db.add(Club(id=id,name=name,description=description,min_age=7,max_age=10,city='Архангельск',address=f'Учебный адрес, {i+1}',phone=f'+7 (000) 000-00-0{i+1}',price=f'{1800+i*200} ₽ / месяц',photo_url='',archived=False));db.flush()
        db.add(Rule(club_id=id,metric=metric,minimum=0,maximum=67 if metric!='any' else 100,priority=10 if metric!='any' else 0,explanation=explanation))
    from .age_tasks import SCENARIOS
    for scenario in SCENARIOS.values():
        if not db.get(TaskSet,scenario['id']):db.add(TaskSet(id=scenario['id'],code=scenario['code'],version=scenario['version'],tasks=scenario['tasks'],active=True))
    db.commit()

if __name__=='__main__':
    with SessionLocal() as db:seed(db)
