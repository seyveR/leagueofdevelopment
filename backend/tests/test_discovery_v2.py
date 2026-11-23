from uuid import uuid4
import pytest
from collections import Counter
from app.discovery_v21 import SETS,VERSION,evaluate
from app.journey_content import DIRECTIONS
from .conftest import register
from .test_api import create_child

def response(task,good=True,interest='0'):
    cfg=task['config']
    if task['mechanic']=='preference':return {'selected':[interest]}
    correct=cfg['key']
    if good:return {'selected':correct}
    if task['mechanic']=='order':return {'selected':list(reversed(correct))}
    return {'selected':[next(c['id'] for c in cfg['choices'] if c['id'] not in correct)]}

@pytest.mark.parametrize('age,group,count',[(5,'4-7',20),(9,'8-10',30),(13,'11-14',40),(17,'15-17',50)])
def test_full_age_sets_resume_thresholds_and_matching(client,age,group,count):
    register(client);child=create_child(client,age);spec=SETS[group]
    assert len(spec['tasks'])==count
    assert set(Counter(t['direction'] for t in spec['tasks']).values())=={count//5}
    assert len({t['id'] for t in spec['tasks']})==count
    if age>=11:assert not any(t['mechanic'] in ('draw','route') for t in spec['tasks'])
    catalog=client.get('/api/journey',params={'child_id':child['id']}).json();assert catalog['count']==count
    session=client.post('/api/journey/start',json={'child_id':child['id'],'request_id':str(uuid4())}).json();id=session['id'];assert session['algorithm_version']==VERSION
    for i,task in enumerate(spec['tasks']):
        detail=client.get('/api/journey/'+id).json();assert detail['session']['position']==i and detail['total']==count
        assert 'key' not in detail['task']['config'] and 'preference_weights' not in detail['task']['config']
        body={'task_id':task['id'],'payload':response(task,task['direction']=='sport','0' if task['direction']=='sport' else '2')}
        saved=client.post('/api/journey/'+id+'/answers',json=body);assert saved.status_code==200,saved.text
        assert client.post('/api/journey/'+id+'/answers',json=body).json()['position']==i+1
    finished=client.post('/api/sessions/'+id+'/complete');assert finished.status_code==200,finished.text
    scores=finished.json()['scores'];assert scores['completed']==count
    assert [d['code'] for d in scores['directions']]==['sport'] and not scores['alternatives']
    assert scores['performance']['sport']==100
    recs=client.get('/api/market/recommendations/'+id).json();assert recs and all('атлетик' in r['club']['name'].lower() or 'гимнастик' in r['club']['name'].lower() for r in recs)
    assert client.post('/api/sessions/'+id+'/complete').json()['id']==finished.json()['id']

def test_no_forced_recommendations_and_no_direct_interest_questions():
    for spec in SETS.values():
        assert all(t['mechanic']!='preference' and not t['prompt'].startswith('Хочешь') for t in spec['tasks'])
    tasks=SETS['15-17']['tasks']
    answers={t['id']:response(t,False) for t in tasks}
    result=evaluate(tasks,answers)
    assert not result['recommended_codes'] and not result['directions'] and result['support']
    assert not result['preferences'] and not result['exploratory']
    for t in tasks:
        if t['direction']=='art':answers[t['id']]=response(t)
    result=evaluate(tasks,answers)
    assert result['recommended_codes']==['art'] and result['directions'][0]['code']=='art'
    sixth=tasks[5]
    assert 'каждый раз используя полученное число' in sixth['prompt']
    assert next(c['label'] for c in sixth['config']['choices'] if c['id']==sixth['config']['key'][0])=='17'


def test_perfect_all_directions_have_conditional_alternatives():
    tasks=SETS['8-10']['tasks'];result=evaluate(tasks,{t['id']:response(t) for t in tasks})
    assert len(result['directions'])==1 and len(result['alternatives'])==2
    assert set(result['performance'].values())=={100}
    assert not result['preferences']
