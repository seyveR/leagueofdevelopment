"""Original familiarisation tasks. No imported psychometric content or norms."""
from itertools import permutations
from uuid import uuid5,NAMESPACE_DNS

LABELS={'attention':'Внимание','memory':'Память','logic':'Логические задачи','spatial':'Пространственные задачи','coordination':'Точность действий','pace':'Планомерное выполнение'}
def choice(id,category,prompt,stimulus,labels,answer=0,mechanic='choice'):
    return {'id':id,'category':category,'prompt':prompt,'stimulus':stimulus,'options':[{'id':f'o{i}','label':v} for i,v in enumerate(labels)],'correct':f'o{answer}','mechanic':mechanic}
def make(group):
    preschool=group=='3-5';older=group in ('10-12','13-17');teen=group=='13-17'
    templates=[
        ('attention','Найди цветок.' if preschool else 'Найди символ, который встречается один раз.','🌼 🍎 🚗' if preschool else '◆ ◇ ◆ ● ◇ ◆',['🌼','🍎','🚗'] if preschool else ['◆','◇','●'],0 if preschool else 2,'search'),
        ('memory','Запомни, кто здесь был.' if preschool else 'Выбери порядок, который ты запомнил.','🐈 🐕' if preschool else ('◆ ● ▲ ■ ★' if teen else '◆ ● ▲'),['🐈 🐕','🐕 🐇','🐈 🐇'] if preschool else ([ '◆ ● ▲ ■ ★','◆ ▲ ● ■ ★','★ ◆ ● ▲ ■'] if teen else ['◆ ● ▲','● ◆ ▲','▲ ● ◆']),0,'memory'),
        ('logic','Что идёт дальше?' if preschool else 'Продолжи закономерность.','● ▲ ● ▲ ?' if preschool else ('2 → 6 → 18 → ?' if teen else '3 → 6 → 12 → ?' if older else '2 → 4 → 6 → ?'),['●','▲','■'] if preschool else (['36','54','72'] if teen else ['18','24','30'] if older else ['7','8','10']),0 if preschool else 1,'sequence'),
        ('spatial','Найди такой же узор.','● ■' if preschool else ('↗ → ↘ ↓' if teen else '■ ● ▲'),['● ■','■ ●','● ●'] if preschool else (['↙ ← ↖ ↑','↗ → ↘ ↓','↑ ↖ ← ↙'] if teen else ['▲ ● ■','■ ▲ ●','■ ● ▲']),0 if preschool else 1 if teen else 2,'choice'),
        ('coordination','Нажми на большую точку.' if preschool else 'Нажми на отмеченную точку.','Точка в центре' if preschool else 'Отмеченная точка справа',['●','○','○'] if preschool else ['○','○','●'],0 if preschool else 2,'target'),
        ('pace','Выбери два одинаковых рисунка.' if preschool else 'Проверь каждый шаг и выбери верную цепочку.','🍎 🍎' if preschool else ('5 × 4 − 7 = ?' if teen else '4 + 3 − 2 = ?' if older else '1 → 2 → 3'),['🍎 🍎','🍎 🚗','🚗 🌼'] if preschool else (['11','12','13'] if teen else ['4','5','6'] if older else ['1 → 2 → 3','1 → 3 → 2','3 → 2 → 1']),0 if preschool else 2 if teen else 1 if older else 0,'choice'),
        ('attention','Найди машинку.' if preschool else 'Сколько пар одинаковых соседей?','🍎 🚗 🌼' if preschool else ('▲ ▲ ● ● ◆ ◆ ★ ★' if older else '▲ ▲ ● ◆ ◆'),['🍎','🚗','🌼'] if preschool else (['3','4','5'] if older else ['1','2','3']),1,'search'),
        ('memory','Какой рисунок ты запомнил?' if preschool else 'Какой символ был последним?','🐇' if preschool else ('▲ ◆ ★ ● ■' if older else '▲ ◆ ★'),['🐈','🐇','🐕'] if preschool else (['■','●','★'] if older else ['◆','★','▲']),1 if preschool or not older else 0,'memory'),
        ('logic','Соедини рисунки с похожими формами.' if preschool else 'Сопоставь выражения и результаты.','' if preschool else ('11 × 3, 7 × 4, 9 × 5' if teen else '6 × 3, 5 × 4, 7 × 2' if older else '2 + 1, 2 + 2, 2 + 3'),[],0,'match'),
        ('spatial','Куда показывает стрелка?','→' if preschool else ('↑ → ↓ ← ↑ ?' if older else '↑ → ↓ ?'),['Вправо','Влево','Вверх'] if preschool else ['→','←','↑'],0 if preschool or older else 1,'sequence'),
        ('coordination','Нажми на отмеченную точку.','Отмеченная точка слева',['●','○','○'],0,'target'),
        ('pace','Найди одинаковые пары.' if preschool else 'Выполни последний шаг по правилу.','🌼 🌼' if preschool else ('Прибавь 7, затем раздели на 3: 14 → ?' if teen else 'Удвой число и прибавь 1: 6 → ?' if older else 'Сначала 3, затем ещё 2: ?'),['🌼 🌼','🌼 🚗','🚗 🍎'] if preschool else (['5','6','7'] if teen else ['11','12','13'] if older else ['4','5','6']),0 if preschool else 2 if teen or older else 1,'choice')]
    tasks=[]
    for n,(category,prompt,stimulus,labels,correct,mechanic) in enumerate(templates):
        t=choice(f'{group}-t{n+1:02}',category,prompt,stimulus,labels,correct,mechanic)
        if mechanic=='match':
            t['left']=['⚽','🎲','🔺'] if preschool else (['11 × 3','7 × 4','9 × 5'] if teen else ['6 × 3','5 × 4','7 × 2'] if older else ['2 + 1','2 + 2','2 + 3'])
            t['right']=['●','■','▲'] if preschool else (['33','28','45'] if teen else ['18','20','14'] if older else ['3','4','5'])
            t['options']=[{'id':f'o{i}','label':' · '.join(t['right'][v] for v in p),'mapping':list(p)} for i,p in enumerate(permutations(range(3)))]
            t['correct']='o0'
        # Level 2 repeats the skill with more distractors, without silently changing age.
        advanced={**t,'id':t['id']+'-d2','difficulty':2}
        if mechanic=='memory':
            advanced['stimulus']='○ '+stimulus
            if n==1:advanced['options']=[{**o,'label':'○ '+o['label']} for o in t['options']]
        if mechanic=='target':advanced['options']=[*t['options'],{'id':'o3','label':'○'}]
        if mechanic=='match':
            advanced['left']=[*t['left'],'⭐' if preschool else '8 + 8'];advanced['right']=[*t['right'],'★' if preschool else '16']
            advanced['options']=[{'id':f'o{i}','label':' · '.join(advanced['right'][v] for v in p),'mapping':list(p)} for i,p in enumerate(permutations(range(4)))]
        if mechanic not in ('match','memory','target'):
            advanced['options']=[*t['options'],{'id':'o3','label':'Другой вариант' if not preschool else '⭐'}]
        tasks.append({**t,'difficulty':1,'advanced':advanced})
    return {'id':str(uuid5(NAMESPACE_DNS,'liga.age.'+group+'.1')),'code':'age-'+group,'version':'2.0.0','tasks':tasks,'min_age':int(group.split('-')[0]),'max_age':int(group.split('-')[1])}
SCENARIOS={group:make(group) for group in ['3-5','6-9','10-12','13-17']}
def group_for(age):return next((s for s in SCENARIOS.values() if s['min_age']<=age<=s['max_age']),None)
def task_variant(task,level):return {k:v for k,v in (task['advanced'] if level==2 else task).items() if k!='advanced'}
