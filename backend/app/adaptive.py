from .models import TaskSet
from .age_tasks import task_variant
RULES_VERSION='adaptive-1.0.0'
def tasks_for(db,session):
    return [item['task'] for item in session.task_trace] if session.task_trace else db.get(TaskSet,session.task_set_id).tasks
def next_task(db,session,correct):
    from .preferences import effective
    from .models import Child
    trace=list(session.task_trace)
    if not trace:return
    child=db.get(Child,session.child_id)
    trace[-1]={**trace[-1],'correct':correct,'conditions':effective(db,child.owner_id,child.id)}
    if session.position<12:
        level=2 if len(trace)>=2 and all(x.get('correct') for x in trace[-2:]) else 1
        slot=db.get(TaskSet,session.task_set_id).tasks[session.position]
        trace.append({'task':task_variant(slot,level),'difficulty':level,'rules_version':RULES_VERSION})
    session.task_trace=trace

def evaluate(tasks,answers,conditions):
    scores={}
    for category in dict.fromkeys(t['category'] for t in tasks):
        group=[t for t in tasks if t['category']==category];correct=sum(answers.get(t['id'])==t['correct'] for t in group)
        scores[category]={'correct':correct,'total':len(group),'percent':round(correct/len(group)*100,1)}
    return {'completed':len(answers),'correct':sum(v['correct'] for v in scores.values()),'total':len(tasks),**scores,'conditions':conditions,
            'comment':'Доли верных действий в ознакомительном наборе. Это не оценка личности, усидчивости, IQ или типа мышления.'}
