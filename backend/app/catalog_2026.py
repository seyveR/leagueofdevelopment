"""Additive import of the user-supplied catalogue. Never replace partner edits.

Class-to-age conversion is approximate; the original school classes stay visible.
Trial times and capacities are synthetic, as requested for the defense prototype.
"""
from datetime import datetime,timedelta,timezone
from uuid import uuid5,NAMESPACE_URL
from sqlalchemy import select,func
from .models import Club,Rule
from .platform_models import Organization,ProgramInfo,TrialSlot

def uid(value):return str(uuid5(NAMESPACE_URL,'liga/catalog/2026/'+value))

ORGS=[
 ('dnk','Дом научной коллаборации имени М. В. Ломоносова','Программы естественнонаучного и технического профилей.','https://vk.ru/dnk_narfu','Набережная Северной Двины, д. 17, корп. 1','216100 (30-54)'),
 ('vmeste','Студия «Вместе»','Семейная студия: развивающие занятия, подготовка к школе и консультации психолога.','https://vk.ru/vmeste_arh','Пр. Троицкий, д. 157','89022863376'),
 ('pchelka','Школа творческого развития «Пчёлка»','Творческие занятия в Музее изобразительных искусств.','https://vk.ru/pchelka_izo','Пл. Ленина, д. 2','65-35-34'),
 ('feeriya','Школа художественной гимнастики «Феерия»','Художественная гимнастика, хореография и акробатика.','https://vk.ru/feeriya29','Ул. Гайдара, д. 63','89118717647'),
 ('strela','Детская школа бега «Золотая стрела»','Лёгкая атлетика и общая физическая подготовка.','https://vk.ru/kids_running_school','Ул. Гайдара, д. 63','89118717647')]
# key, organisation, name, description, ages, price text/rub, schedule, tags, direction
PROGRAMS=[
 ('bio','dnk','Биотехнология','Базовые компетенции в биотехнологии, проектная и исследовательская деятельность. 10–11 класс.',15,17,'Бесплатно',0,'Чт, 16:30–19:10',['Биология','Исследования','Природа','Генетика','Медицина'],'natural'),
 ('chem','dnk','Лабораторный химический практикум','Основы проведения химического эксперимента. 8 класс.',13,15,'Бесплатно',0,'Пн, 16:00–18:00',['Химия','Эксперименты','Опыты','Исследования'],'natural'),
 ('bioschool','dnk','Биологическая школа','Знакомство с естественными науками, животными и растениями. 2–4 класс.',8,11,'10 500 ₽ за программу',10500,'Каникулы, 10:00–15:00',['Природа','Животные','Растения','Окружающий мир'],'natural'),
 ('robotjunior','dnk','Творческая робототехника','Конструирование, программирование и управление роботами. 5–7 лет, 1 класс.',5,8,'19 200 ₽ за программу',19200,'Сб, 10:00–11:30',['Роботы','Алгоритмы','Управление','Техника'],'technical'),
 ('robot','dnk','Основы робототехники','Проектная деятельность: конструирование, программирование и управление роботами. 5–7 класс.',10,14,'Бесплатно',0,'Сб, 12:30–15:10',['Роботы','Алгоритмы','Управление','Техника'],'technical'),
 ('neuro','dnk','Нейротехнологии в робототехнике','Проектирование нейро- и биоэлектрических интерфейсов на Arduino. Углублённый уровень, 8–11 класс.',13,17,'Бесплатно',0,'Ср, 16:30–19:10',['Роботы','Алгоритмы','Техника','Биология','Нейроинтерфейсы'],'technical'),
 ('python','dnk','Основы программирования на языке Python','Разработка программ и основы языка Python. 7–8 класс.',12,15,'23 400 ₽ за программу',23400,'Пн, 16:30–19:10',['Алгоритмы','Программирование','Компьютерные технологии'],'technical'),
 ('school','vmeste','Подготовка к школе','Обучение чтению, развитие речи, памяти, мышления, моторики и навыков общения.',5,7,'3 600 ₽ в месяц',3600,'Пт, 18:00–18:45',['Подготовка к школе','Буквы','Цифры','Общение','Развитие памяти'],'social'),
 ('sand','vmeste','Песочная терапия','Индивидуальная консультация психолога с использованием песка. От 5 лет.',5,17,'2 500 ₽ за консультацию',2500,'По согласованию',['Психолог','Консультация'],'consultation'),
 ('career','vmeste','Профориентация','Обсуждение интересов, целей и будущей профессии с психологом. 7–11 класс.',12,17,'4 000 ₽ в месяц',4000,'По согласованию',['Психолог','Профессия','Интересы'],'social'),
 ('art','pchelka','Занятия для детей 3–6 лет','Игры-путешествия по музею, декоративно-прикладное творчество, музыка и рисование.',3,6,'550 ₽ за занятие',550,'Сб, с 10:00',['Творчество','Рисование','Музыка','Музей','Пение','Искусство','Лепка'],'art'),
 ('gym3','feeriya','Художественная гимнастика · 3–4 года','Гимнастика, хореография и общая физическая подготовка для начинающих.',3,4,'4 800 ₽ в месяц',4800,'Вт, чт, 18:30–19:15',['Гимнастика','ОФП','Спорт','Танцы'],'sport'),
 ('gym4','feeriya','Художественная гимнастика · 4–5 лет','Гимнастика, хореография и общая физическая подготовка.',4,5,'7 200 ₽ в месяц',7200,'Пн, вт, чт, 17:00–18:30',['Гимнастика','ОФП','Спорт','Танцы'],'sport'),
 ('running','strela','Лёгкая атлетика и общая физическая подготовка','Тренировки по лёгкой атлетике, бег и общая физическая подготовка. Группы с 3 лет.',3,17,'5 000 ₽ в месяц',5000,'Пн, ср, пт, 16:00–18:00',['Бег','Лёгкая атлетика','Спорт','Физкультура'],'sport')]

def seed(db):
    for key,name,description,contact,address,phone in ORGS:
        if not db.get(Organization,uid('org/'+key)):
            db.add(Organization(id=uid('org/'+key),name=name,description=description,contact=contact,city='Архангельск',status='approved'))
    db.flush()
    orgs={o[0]:o for o in ORGS}
    for key,org,name,description,low,high,price,rub,schedule,tags,direction in PROGRAMS:
        id=uid('program/'+key)
        if db.get(Club,id):continue
        _,_,_,_,address,phone=orgs[org]
        photo='laboratory' if direction=='natural' else 'robot' if direction=='technical' else 'sport' if direction=='sport' else 'art'
        db.add(Club(id=id,name=name,description=description,min_age=low,max_age=high,city='Архангельск',address=address,phone=phone,price=price,photo_url=f'/catalog/{photo}.jpg',archived=False));db.flush()
        db.add(ProgramInfo(club_id=id,organization_id=uid('org/'+org),price_rub=rub,format='offline',tags=tags+[f'direction:{direction}'],schedule=schedule,status='approved'))
        db.add(Rule(club_id=id,metric='any',priority=0,minimum=0,maximum=100,explanation='Подбор по возрасту и интересам.'))
    db.flush()
    refresh_slots(db)

def refresh_slots(db):
    """Maintain two future sample slots per imported programme, without touching bookings."""
    from zoneinfo import ZoneInfo
    current=datetime.now(timezone.utc)
    for i,program in enumerate(PROGRAMS):
        club_id=uid('program/'+program[0])
        future=db.scalar(select(func.count()).select_from(TrialSlot).where(TrialSlot.club_id==club_id,TrialSlot.enabled==True,TrialSlot.starts_at>current))
        if future>=2:continue
        for offset in (2,9):
            day=(current+timedelta(days=offset+i%4)).astimezone(ZoneInfo('Europe/Moscow')).replace(hour=16+i%3,minute=30 if i%2 else 0,second=0,microsecond=0)
            id=uid(f'slot/{club_id}/{day.isoformat()}')
            if not db.get(TrialSlot,id):db.add(TrialSlot(id=id,club_id=club_id,starts_at=day,capacity=[6,8,10][i%3],enabled=True))
