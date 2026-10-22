VERSION = 'answers-1.0.0'

def evaluate(tasks: list[dict], answers: dict[str, str]) -> dict:
    groups = {}
    for group in ('attention','memory'):
        selected = [t for t in tasks if t['category'] == group]
        correct = sum(answers.get(t['id']) == t['correct'] for t in selected)
        groups[group] = {'correct': correct, 'total': len(selected), 'percent': round(correct / len(selected) * 100, 1)}
    return {'completed': len(answers), 'correct': sum(g['correct'] for g in groups.values()), 'total':len(tasks), **groups, 'comment':'Показатели отражают выполнение этого набора заданий.'}
