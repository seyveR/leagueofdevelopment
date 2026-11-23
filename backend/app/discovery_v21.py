"""Revision without self-reported interests. Historical v2 sets stay immutable."""
from uuid import uuid5,NAMESPACE_URL
from copy import deepcopy
from .discovery_v2 import SETS as PREVIOUS,decision
from .journey_content import DIRECTIONS
VERSION='discovery-2.1.0'

REPLACEMENTS={
 'technical':[
  decision('Нужно соединить две детали винтом. Что взять?',['🪛 Отвёртку','🖌️ Кисточку','🥄 Ложку']),
  decision('Для одной модели нужны 4 колеса. Сколько колёс нужно для трёх моделей?',['12','7','16']),
  decision('Нужно проверить, выдержит ли модель моста груз 2 кг. Какой результат подтвердит выполнение требования?',['Мост выдерживает 2 кг без разрушения при проверке','Модель красиво выглядит','Автор уверен, что мост прочный']),
  decision('Приложение должно загружать отчёт не дольше 3 секунд. Какая проверка соответствует требованию?',['Измерить время загрузки отчёта в заданных условиях','Спросить разработчика, быстро ли оно работает','Проверить только цвет кнопки'])],
 'natural':[
  decision('У растения сухая земля. Что сделать?',['💧 Полить растение','🧸 Положить игрушку','📦 Закрыть коробкой']),
  decision('Как измерить, насколько выросло растение за неделю?',['Измерить высоту в начале и конце недели','Один раз посмотреть на цвет листьев','Сравнить цвет двух разных горшков']),
  decision('Растворили 10 г соли в 90 г воды. Какова масса раствора?',['100 г','90 г','80 г']),
  decision('В 20 пробах измерили один показатель. Одно значение резко отличается. Что сделать перед выводами?',['Проверить запись, условия измерения и возможную причину отклонения','Удалить значение только потому, что оно неудобное','Использовать только это значение'])],
 'art':[
  decision('Смешали красную и жёлтую краску. Какой цвет получится?',['🟠 Оранжевый','🟢 Зелёный','🔵 Синий']),
  decision('Надпись на рисунке закрывает лицо героя. Как сохранить и героя, и надпись?',['Перенести надпись в свободное место','Закрасить героя целиком','Добавить ещё одну надпись поверх лица']),
  decision('Плакат будут читать издалека. Как лучше оформить время и место события?',['Крупно, контрастно и в заметном месте','Очень мелко у края листа','Сделать текст того же цвета, что и фон']),
  decision('Один макет нужен для экрана телефона и большого печатного плаката. Как подготовить материалы?',['Адаптировать размеры, расположение и читаемость под каждый формат','Растянуть маленький снимок экрана для печати','Использовать один размер текста независимо от носителя'])],
 'social':[
  decision('Друг рассказывает, где потерял игрушку. Как понять, где искать?',['👂 Послушать и спросить, где он играл','🙉 Перебить и не слушать','😠 Начать спорить']),
  decision('В приглашении сказано: «Встреча в субботу в 12:00». Чего не хватает, чтобы прийти?',['Места встречи','Цвета бумаги','Имени любимого героя']),
  decision('В сообщении сказано: «Срок перенесли со вторника на четверг». Что изменилось?',['Завершить работу нужно в четверг вместо вторника','Работу отменили','Работу нужно завершить раньше вторника']),
  decision('В сообщении утверждают: «Наш способ лучший», но нет критериев и данных. Какой вопрос поможет проверить утверждение?',['По каким показателям и с какими альтернативами его сравнивали?','Почему сообщение такое короткое?','Можно ли написать это крупнее?'])],
 'sport':[
  decision('Перед тобой низкая перекладина. Как пройти под ней?',['🙆 Пригнуться','🧍 Выпрямиться ещё сильнее','🙈 Закрыть глаза и идти']),
  decision('Эстафетную палочку нужно передать следующему участнику. Что сделать?',['Передать её в обозначенном месте по правилам эстафеты','Бросить палочку в сторону зрителей','Унести её с площадки']),
  decision('Участник пробежал 600 м за 3 минуты в постоянном темпе. Сколько метров он пробежит за 5 минут в том же темпе?',['1000 м','900 м','1200 м']),
  decision('В турнире на выбывание участвуют 8 команд. После поражения команда выбывает. Сколько матчей нужно, чтобы определить одного победителя?',['7','8','14'])]
}

def make_set(group,spec,level):
    tasks=deepcopy(spec['tasks'])
    for task in tasks:
        if task['mechanic']=='preference':
            replacement=deepcopy(REPLACEMENTS[task['direction']][level])
            task.update(replacement)
        if group=='15-17' and task['id']=='v2-technical-6':
            task['prompt']='На экране число 3. Один шаг: умножить текущее число на 2 и вычесть 1. Выполни три таких шага подряд, каждый раз используя полученное число. Какое число будет на экране в конце?'
        if task['mechanic']=='decision':
            choices=task['config']['choices'];shift=(tasks.index(task)+level)%len(choices)
            task['config']['choices']=choices[shift:]+choices[:shift]
    return {**spec,'id':str(uuid5(NAMESPACE_URL,f'liga/discovery/{group}/2.1')),'version':'2.1.0','tasks':tasks}

SETS={group:make_set(group,spec,i) for i,(group,spec) in enumerate(PREVIOUS.items())}

def evaluate(tasks,answers):
    from .journey_assessment import score_task
    groups={k:[] for k in DIRECTIONS};details=[]
    for task in tasks:
        value=score_task(task,answers[task['id']])
        if task['mechanic']=='order':value={'correct':int(value['correct']==value['total']),'total':1}
        groups[task['direction']].append(value['correct']/value['total'])
        details.append({'task_id':task['id'],'prompt':task['prompt'],'metric':task['direction'],'score':value})
    performance={k:round(sum(v)/len(v)*100,1) for k,v in groups.items()}
    ranked=sorted(DIRECTIONS,key=lambda k:(-performance[k],k))
    main=[k for k in ranked if performance[k]>=70][:1]
    alternatives=[k for k in ranked if main and k not in main and performance[k]>=60 and performance[k]>=performance[main[0]]-15][:2]
    def item(k):return {'code':k,'name':DIRECTIONS[k],'reason':f'Выполнение заданий направления: {performance[k]}%.'}
    return {'completed':len(answers),'total':len(tasks),'correct':sum(d['score']['correct'] for d in details),'test_name':'Возрастной маршрут','test_code':'discovery','scored':False,'comment':'',
        'task_details':details,'performance':performance,'affinities':performance,'preferences':{},'directions':[item(k) for k in main],
        'alternatives':[item(k) for k in alternatives],'exploratory':[],
        'support':[{'code':k,'name':DIRECTIONS[k],'message':'Попробуйте ещё раз разобрать задания этого направления без спешки.'} for k in ranked if performance[k]<60],
        'recommended_codes':main+alternatives,'selection_version':'thresholds-2.0.0'}
