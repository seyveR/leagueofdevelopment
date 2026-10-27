"""Export exact runtime texts for external recording; no network or paid generation."""
import hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.audio_content import SAMPLE,INSTRUCTION,MEMORY
from app.content import TASKS
from app.age_tasks import SCENARIOS

texts=[SAMPLE,INSTRUCTION,MEMORY,'Готово. Ответы сохранены. Можно посмотреть результаты.']
texts += [task['prompt'] for task in TASKS]
texts += [task['prompt'] for scenario in SCENARIOS.values() for task in scenario['tasks']]
texts=list(dict.fromkeys(texts))
voices=[{'id':'ru-lev','character':'Лев','provider_voice':'Мальчик Петя','sample':'references/audio/lev-petya-sample.mp3'},
        {'id':'ru-sofia','character':'София','provider_voice':'Девочка Таня','sample':'references/audio/sofia-tanya-sample.mp3'}]
out=ROOT/'voice-recording';out.mkdir(exist_ok=True)
for voice in voices:
    voice['sample_sha256']=hashlib.sha256((ROOT/voice['sample']).read_bytes()).hexdigest()
job={'schema_version':1,'provider':'Звукограм','status':'voices_selected_recordings_pending',
     'settings':'Use settings approved by the user; verify speed, pitch, style before generation.',
     'voices':voices,'texts':[{'id':f'{n:03}','text':text,'sha256':hashlib.sha256(text.encode()).hexdigest()} for n,text in enumerate(texts,1)]}
(out/'job.json').write_text(json.dumps(job,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# These files contain only text to pronounce. IDs and instructions are in job.json.
for voice in voices:
    (out/(voice['id']+'-texts.txt')).write_text('\n\n'.join(texts)+'\n',encoding='utf-8')
print(f'{len(texts)} unique texts per voice; {sum(map(len,texts))} characters per voice; {len(texts)*2} recordings required')
