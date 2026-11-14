from uuid import uuid5,NAMESPACE_URL
from .age_tasks import SCENARIOS

VERSION='domains-1.0.0'
NAMES={'attention':'Внимание','memory':'Память','logic':'Логика','spatial':'Пространственное мышление','imagination':'Воображение'}
DESCRIPTIONS={'attention':'Находи детали и проверяй совпадения.','memory':'Запоминай и восстанавливай последовательности.','logic':'Находи правила и продолжай ряды.','spatial':'Разбирайся в расположении и поворотах.','imagination':'Выбирай продолжения образов и историй. Верных и неверных вариантов нет.'}

def make_set(group,code):
    source=SCENARIOS[group]['tasks'];tasks=[]
    for n in range(6):
        if code=='imagination':
            prompts=['Во что может превратиться круг?','Выбери продолжение истории о путешествии.','Каким будет твой необычный дом?','Что можно придумать из двух треугольников?','Выбери спутника для новой истории.','Какое открытие сделает твой герой?']
            labels=[['Планета','Колесо','Воздушный шар'],['Новая тропинка','Встреча с другом','Необычная находка'],['Сад на крыше','Дом на воде','Башня с окнами'],['Парус','Горы','Крылья'],['Робот','Птица','Исследователь'],['Новый цвет','Скрытый остров','Звучащий камень']][n]
            task={'category':code,'prompt':prompts[n],'stimulus':['○','Дорога → ?','Дом → ?','△ △','Спутник → ?','Открытие → ?'][n],'options':[{'id':f'o{i}','label':v} for i,v in enumerate(labels)],'correct':'o0','scored':False,'mechanic':'choice'}
        else:
            candidates=[t for t in source if t['category']==code]
            base=candidates[n%len(candidates)]
            task={k:v for k,v in base.items() if k!='advanced'}
            # Variants reverse both material and candidates consistently, not six identical prompts.
            if n>=2:
                task['options']=list(reversed(task['options']))
                if task.get('mechanic')!='match':task['prompt']+=' '+['Посмотри внимательно.','Проверь свой выбор.'][n%2]
            task['scored']=True
        if code!='imagination':
            young=group=='3-5';older=group in ('10-12','13-17')
            symbols=['●','▲','■','◆','★','○','△','□']
            if code=='attention':
                count=(2 if young else 4 if older else 3)+n%3
                material=['▲']*count+['●']*(n%2+1)+['■']
                material=material[n%len(material):]+material[:n%len(material)]
                prompt='Сколько треугольников в ряду?';stimulus=' '.join(material);labels=[str(count-1),str(count),str(count+1)];correct=1
            elif code=='memory':
                length=2 if young else 5 if older else 3
                sequence=[symbols[(n+i)%len(symbols)] for i in range(length)]
                prompt='Выберите порядок фигур, который вы запомнили.';stimulus=' '.join(sequence)
                labels=[' '.join(sequence),' '.join(reversed(sequence)),' '.join(sequence[1:]+sequence[:1])];correct=0
            elif code=='logic':
                if young:
                    a,b=symbols[n],symbols[(n+1)%len(symbols)];stimulus=f'{a} {b} {a} {b} ?';labels=[a,b,symbols[(n+2)%len(symbols)]];correct=0
                else:
                    a=n+2;step=3 if older else 2;stimulus=f'{a} → {a+step} → {a+2*step} → ?';labels=[str(a+3*step),str(a+2*step+1),str(a+4*step)];correct=0
                prompt='Продолжи закономерность.'
            else:
                arrows=['↑','→','↓','←'];index=n%4
                prompt='Куда показывает стрелка?' if young else 'Поверни стрелку на четверть оборота по часовой стрелке.'
                stimulus=arrows[index];right=index if young else (index+1)%4
                labels=(['Вверх','Вправо','Вниз','Влево'] if young else arrows);correct=right
                if n>=4:
                    prompt='Что находится справа от круга?' if n==4 else 'Что находится слева от квадрата?'
                    stimulus='● ▲ ■' if n==4 else '▲ ● ■'
                    labels=['Круг','Треугольник','Квадрат'];correct=1 if n==4 else 0
            task={'category':code,'prompt':prompt,'stimulus':stimulus,'options':[{'id':f'o{i}','label':v} for i,v in enumerate(labels)],'correct':f'o{correct}','scored':True,'mechanic':'memory' if code=='memory' else 'choice'}
        tasks.append({**task,'id':f'{code}-{n+1}','difficulty':1})
    return {'id':str(uuid5(NAMESPACE_URL,f'liga/domains/{group}/{code}/1')), 'code':f'domain-{code}-{group}','version':'1.0.0','tasks':tasks}

SETS={(g,c):make_set(g,c) for g in SCENARIOS for c in NAMES}

