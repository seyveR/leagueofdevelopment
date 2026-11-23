"""Original age-specific activities, versioned independently of legacy tests.

Mechanics inspired by part 1 of the supplied brief; no borrowed test items,
age norms, AI scoring, or assessment of artistic quality.
"""
from uuid import uuid5, NAMESPACE_URL

VERSION = 'discovery-1.0.0'
GROUPS = [(4, 7), (8, 10), (11, 14), (15, 17)]
LABELS = {'logic':'Логические задания','memory':'Зрительная память','attention':'Поиск деталей','spatial':'Маршрут','story':'Последовательность событий'}
DIRECTIONS = {'technical':'Техника и программирование','natural':'Природа и исследования','art':'Творчество','social':'Общение и языки','sport':'Спорт и движение'}

def group_for(age):
    return next(((a,b) for a,b in GROUPS if a<=age<=b), None)

def items(labels):
    return [{'id':str(i),'label':label} for i,label in enumerate(labels)]

def make_set(level, ages):
    def task(n, mechanic, category, prompt, **config):
        return {'id':f'd{n}', 'mechanic':mechanic, 'category':category,
                'prompt':prompt, 'stimulus':'', 'options':[], 'config':config}
    young = level==0
    scenarios = [
        ('Пошёл дождь. Разложи последствия: что помогает растениям, а что мешает прогулке.', ['🌱 Цветы получают воду','👕 Одежда промокла','🌳 Деревья получают воду','🛝 Горка стала скользкой']),
        ('В школе выключили свет. Раздели последствия на полезные для экономии и мешающие работе.', ['💡 Лампы не тратят электричество','💻 Компьютер без батареи выключился','🔌 Приборы не расходуют энергию','🔬 Микроскоп с подсветкой не работает']),
        ('Город запустил электробусы. Раздели последствия на преимущества и ограничения.', ['🌿 Нет выхлопа на маршруте','🔋 Нужно время на зарядку','🔈 Меньше шума двигателя','⚡ Нужна зарядная инфраструктура']),
        ('Школа перешла на электронные учебники. Раздели преимущества и ограничения.', ['📚 Меньше вес рюкзака','🔋 Нужен заряженный планшет','🔎 Можно искать слова в тексте','☀️ Блики на экране мешают чтению'])
    ]
    odd_labels = [['🍎 Яблоко','🍐 Груша','🍌 Банан','🚗 Машина'],['🔨 Молоток','🪚 Пила','🪛 Отвёртка','🎻 Скрипка'],['🔺 Треугольник','🟦 Квадрат','⬡ Шестиугольник','⚪ Круг'],['2','3','5','9']][level]
    reasons = [['Три предмета — фрукты','Все одного цвета','Все одинаковой формы'],['Три предмета — инструменты для работы','Все музыкальные','Все деревянные'],['Три фигуры имеют углы','Все одного цвета','Все круглые'],['Три числа простые','Все числа чётные','Все кратны трём']][level]
    patterns = [
        [('🔵 🟡 🔵 🟡 ?', ['🔵','🟡','🟩']), ('▲ ■ ▲ ■ ?', ['▲','■','●']), ('🍎 🍎 🍐 🍎 🍎 ?', ['🍐','🍎','🍋'])],
        [('2 · 4 · 6 · ?', ['8','7','10']), ('🔵 🔵 🟡 🔵 🔵 ?', ['🟡','🔵','🟩']), ('1 · 3 · 5 · ?', ['7','6','9'])],
        [('3 · 6 · 12 · ?', ['24','18','21']), ('1 · 4 · 9 · ?', ['16','12','15']), ('2 · 3 · 5 · 8 · ?', ['12','11','13'])],
        [('2 · 6 · 12 · 20 · ?', ['30','28','32']), ('1 · 1 · 2 · 3 · 5 · ?', ['8','7','10']), ('81 · 27 · 9 · ?', ['3','6','0'])]
    ][level]
    # Deterministically rotate candidates: the correct choice is not always first.
    sequences=[]; pattern_key=[]
    for i,(text,labels) in enumerate(patterns):
        shift=(level+i)%3; rotated=labels[shift:]+labels[:shift]
        sequences.append({'text':text,'choices':items(rotated)})
        pattern_key.append(str(rotated.index(labels[0])))
    pool=['🍎','🚲','🌳','⭐','🐈','🌙','🎈','🔑','☂️','📚','🌻','⏰','🦋','🎵','🚀','🎲']
    length=[3,5,7,8][level]
    targets=[str(i) for i in range(length)]
    memory_items=items(pool[:length+4]); memory_items=memory_items[2:]+memory_items[:2]
    steps=[['right','up','right'],['right','up','left','up','right'],['up','right','right','down','left','down'],['left','up','up','right','right','down','left','down']][level]
    grid_size=[4,5,6,6][level]
    attention=items(['★' if (i*7+level)%5==0 else ['☆','✦','✧'][(i+level)%3] for i in range(grid_size**2)])
    attention_key=[x['id'] for x in attention if x['label']=='★']
    stories=[['🌱 Посадили семечко','💧 Полили землю','🌿 Появился росток','🌻 Распустился цветок'],['📝 Нарисовали план','🧱 Собрали детали','🔧 Проверили модель','🏁 Запустили машинку'],['❓ Задали вопрос','💡 Предложили гипотезу','🔬 Провели опыт','📊 Сравнили результат с гипотезой'],['🔎 Изучили запрос пользователей','📝 Подготовили прототип','👥 Провели проверку с пользователями','🛠️ Доработали по обратной связи']][level]
    story_items=items(stories); story_items=story_items[2:]+story_items[:2]
    title=['Коробка превращается','Создай полезный предмет','Спроектируй новое устройство','Предложи решение для школы'][level]
    combinations=[['🏠 Домик из коробки','🥁 Барабан','🚗 Машинка','🌱 Мини-сад','🎭 Сцена'],['🏠 Макет дома','🤖 Робот из упаковки','🌱 Кашпо','🎭 Театр теней','🎨 Органайзер для красок'],['☀️ Солнечный светильник','🌿 Система полива','🎨 Световая инсталляция','🎭 Сценический реквизит','🏀 Табло для игры'],['💻 Планировщик задач','🌿 Монитор качества воздуха','🎨 Дизайн школьной выставки','🤝 Сервис взаимопомощи','🏃 Планировщик тренировок']][level]
    direction_maps=[['art','art','technical','natural','social'],['art','technical','natural','social','art'],['technical','natural','art','social','sport'],['technical','natural','art','social','sport']][level]
    tool_tasks=[
        ('Мяч под диваном. Собери безопасный план: выбрать инструмент и достать мяч.', ['🧹 Взять длинную щётку','↩️ Осторожно выкатить мяч','🛋️ Самому поднять тяжёлый диван','💧 Залить водой'],['0','1']),
        ('Нужно перейти ручей в игре. Собери мост из доступных вещей.', ['🪵 Положить крепкую доску','✅ Проверить опоры','🚶 Перейти по мосту','🌊 Прыгнуть в воду'],['0','1','2']),
        ('Лампа не включается. Собери безопасную последовательность проверки.', ['🔌 Отключить питание','🔎 Проверить кабель с взрослым','💡 Заменить повреждённый кабель','⚡ Трогать оголённый провод'],['0','1','2']),
        ('Прототип не работает. Собери последовательность поиска ошибки.', ['📋 Воспроизвести проблему','🔎 Проверить отдельные узлы','🛠️ Исправить причину','✅ Повторить проверку'],['0','1','2','3'])
    ][level]
    return {'id':str(uuid5(NAMESPACE_URL,f'liga/discovery/{ages[0]}-{ages[1]}/1')),
            'code':f'discovery-{ages[0]}-{ages[1]}','version':'1.0.0','tasks':[
        task(1,'combine','imagination',title+'. Выбери до трёх идей, которые хочется попробовать.',choices=items(combinations),max_select=3,direction_key=direction_maps),
        task(2,'draw','imagination',['Преврати круг в рисунок.','Дорисуй фигуру до нового предмета.','Создай эскиз из геометрической основы.','Нарисуй эскиз полезного объекта.'][level],choices=items(['🎨 Украшение или картина','⚙️ Устройство','🌿 Природный объект','🎭 Персонаж истории']),shape=['circle','triangle','square','hexagon'][level],direction_key=['art','technical','natural','social']),
        task(3,'sort','logic',scenarios[level][0],choices=items(scenarios[level][1]),buckets=['Преимущество','Ограничение'] if not young else ['Помогает растениям','Мешает прогулке'],key=['0','1','0','1']),
        task(4,'order','logic',tool_tasks[0],choices=items(tool_tasks[1]),length=len(tool_tasks[2]),key=tool_tasks[2]),
        task(5,'odd','logic','Найди лишний элемент и выбери объяснение.',choices=items(odd_labels),reasons=items(reasons),key={'item':'3','reason':'0'}),
        task(6,'patterns','logic','Заполни три пропуска в закономерностях.',sequences=sequences,key=pattern_key),
        task(7,'memory','memory','Запомни картинки. Затем скрой их и отметь те, которые были показаны.',choices=memory_items,material=[pool[int(i)] for i in targets],key=targets),
        task(8,'targets','attention','Найди все закрашенные звёзды ★. Пустые и другие звёзды не выбирай.',choices=attention,columns=grid_size,key=attention_key),
        task(9,'route','spatial','Проведи робота по маршруту. Нажимай стрелки по порядку.',steps=steps,grid=5,start=[2,2],key=steps),
        task(10,'order','story','Собери события по порядку: от начала до результата.',choices=story_items,length=4,key=['0','1','2','3'])]}

SETS={f'{a}-{b}':make_set(i,(a,b)) for i,(a,b) in enumerate(GROUPS)}

def public_task(task, phase):
    cfg={k:v for k,v in task['config'].items() if k not in ('key','direction_key')}
    task=dict(task)
    short={'d1':'Выбери до трёх идей для коробки.','d2':'Дорисуй фигуру.','d3':'Идёт дождь. Что помогает растениям, а что мешает гулять?','d4':'Как достать мяч из-под дивана? Покажи по порядку.','d5':'Что здесь лишнее? Почему?','d6':'Что будет дальше?','d7':'Запомни картинки. Скрой их и найди снова.','d8':'Найди все закрашенные звёздочки ★.','d9':'Веди робота по стрелкам.','d10':'Что было сначала? Собери историю.'}
    if task['id'] in ('d5','d6','d7','d8','d9','d10') or (task['id']=='d1' and 'Коробка' in task['prompt']) or (task['id']=='d2' and task['config'].get('shape')=='circle') or (task['id']=='d3' and 'дождь' in task['prompt']) or (task['id']=='d4' and 'диван' in task['prompt']):task['prompt']=short.get(task['id'],task['prompt'])
    if task['mechanic']=='memory':
        if phase=='view':cfg.pop('choices',None)
        else:cfg.pop('material',None)
    return {k:task[k] for k in ('id','mechanic','category','prompt')} | {'config':cfg}
