"""Deterministic scoring of observed actions; no psychological age norms."""
from fastapi import HTTPException
from .journey_content import LABELS, DIRECTIONS

def validate(task, payload):
    cfg=task['config']; kind=task['mechanic']; allowed={x['id'] for x in cfg.get('choices',[])}
    def sequence(value, pool, maximum, exact=False):
        if not isinstance(value,list) or len(value)>maximum or (exact and len(value)!=maximum) or any(not isinstance(x,str) or x not in pool for x in value):raise ValueError()
        return value
    try:
        if kind in ('combine','memory','targets','order'):
            if set(payload)!={'selected'}:raise ValueError()
            selected=sequence(payload['selected'],allowed,cfg.get('length',cfg.get('max_select',len(allowed))),kind=='order')
            if len(set(selected))!=len(selected) or (kind=='combine' and not selected):raise ValueError()
        elif kind=='sort':
            if set(payload)!={'buckets'}:raise ValueError()
            sequence(payload['buckets'],{'0','1'},len(allowed),True)
        elif kind=='odd':
            if set(payload)!={'item','reason'} or payload['item'] not in allowed or payload['reason'] not in {x['id'] for x in cfg['reasons']}:raise ValueError()
        elif kind=='patterns':
            if set(payload)!={'selected'}:raise ValueError()
            seq=sequence(payload['selected'],{'0','1','2'},3,True)
            if any(s not in {c['id'] for c in part['choices']} for s,part in zip(seq,cfg['sequences'])):raise ValueError()
        elif kind=='route':
            if set(payload)!={'selected'}:raise ValueError()
            seq=sequence(payload['selected'],{'up','down','left','right'},len(cfg['steps']),True)
            x,y=cfg['start']
            for s in seq:
                dx,dy={'up':(0,-1),'down':(0,1),'left':(-1,0),'right':(1,0)}[s];x+=dx;y+=dy
                if not 0<=x<cfg['grid'] or not 0<=y<cfg['grid']:raise ValueError()
        elif kind=='draw':
            if set(payload)!={'choice','strokes'} or payload['choice'] not in allowed:raise ValueError()
            strokes=payload['strokes']
            if not isinstance(strokes,list) or not 1<=len(strokes)<=80:raise ValueError()
            for stroke in strokes:
                if not isinstance(stroke,list) or not 1<=len(stroke)<=300:raise ValueError()
                for point in stroke:
                    if not isinstance(point,list) or len(point)!=2 or any(type(p) not in (int,float) or not 0<=p<=1 for p in point):raise ValueError()
        else:raise ValueError()
    except (KeyError,TypeError,ValueError):raise HTTPException(422,'Завершите задание и проверьте выбранные элементы')

def score_task(task,payload):
    kind=task['mechanic'];key=task['config'].get('key')
    if kind in ('combine','draw'):return None
    if kind in ('memory','targets'):
        selected=set(payload['selected']);target=set(key)
        found=len(selected&target);wrong=len(selected-target)
        return {'correct':max(0,found-wrong),'total':len(target),'found':found,'wrong':wrong,'missed':len(target-selected)}
    actual=payload['buckets'] if kind=='sort' else [payload['item'],payload['reason']] if kind=='odd' else payload['selected']
    expected=[key['item'],key['reason']] if kind=='odd' else key
    return {'correct':sum(a==b for a,b in zip(actual,expected)),'total':len(expected)}

def evaluate(tasks,answers):
    metrics={}; details=[]; preferences={key:0 for key in DIRECTIONS}
    for task in tasks:
        raw=answers[task['id']];value=score_task(task,raw)
        details.append({'task_id':task['id'],'prompt':task['prompt'],'metric':task['category'],'score':value})
        if value:
            bucket=metrics.setdefault(task['category'],{'correct':0,'total':0})
            bucket['correct']+=value['correct'];bucket['total']+=value['total']
        if task['mechanic']=='combine':
            for item in raw['selected']:preferences[task['config']['direction_key'][int(item)]]+=1
        if task['mechanic']=='draw':preferences[task['config']['direction_key'][int(raw['choice'])]]+=1
    for key,value in metrics.items():value['percent']=round(100*value['correct']/value['total'],1)
    # Affinities order exploratory activities, not aptitude scores or probabilities.
    f=lambda k:metrics.get(k,{}).get('percent',0)/100
    affinities={'technical':round(6*f('logic')+4*f('spatial'),2),
                'natural':round(5*f('attention')+5*f('logic'),2),
                'art':round(5*f('spatial')+5*f('story'),2),
                'social':round(6*f('story')+4*f('memory'),2),'sport':round(5*f('attention')+5*f('spatial'),2)}
    for key,count in preferences.items():affinities[key]+=count*3
    ranked=sorted(DIRECTIONS,key=lambda k:(-affinities[k],k))
    return {'completed':len(answers),'total':len(tasks),'correct':sum(v['correct'] for v in metrics.values()),
            'test_name':'Путь открытий','test_code':'discovery','scored':False,
            **metrics,'task_details':details,'preferences':preferences,'affinities':affinities,
            'directions':[{'code':k,'name':DIRECTIONS[k],'reason':reason(k,metrics,preferences)} for k in ranked],
            'comment':'Показатели описывают только действия в этих заданиях. Это не оценка интеллекта, способностей или сравнение с возрастной нормой. Рисунки и необычность идей не оцениваются. Подбор помогает выбрать, что попробовать.'}

def reason(direction,metrics,preferences):
    sources={'technical':['logic','spatial'],'natural':['attention','logic'],'art':['spatial','story'],'social':['story','memory'],'sport':['attention','spatial']}[direction]
    parts=[f"{LABELS[k]}: {metrics[k]['correct']} из {metrics[k]['total']} действий" for k in sources if k in metrics]
    if preferences.get(direction):parts.append('есть выбор этого направления в творческих заданиях')
    return '; '.join(parts)+'.'
