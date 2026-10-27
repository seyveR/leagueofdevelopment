"""Map numbered user recordings to exact job texts; preserve generated WAV fallback."""
import hashlib,json,re,shutil
from pathlib import Path

root=Path(__file__).resolve().parents[1]
job=json.loads((root/'voice-recording/job.json').read_text('utf-8'))
texts={int(row['id']):row['text'] for row in job['texts']}
output=root/'audio-cache';output.mkdir(exist_ok=True)
manifest={'schema_version':1,'voices':{}}
for folder,voice in [('sofia','ru-sofia'),('lev','ru-lev')]:
    entries={}
    for source in sorted((root/'voices'/folder).glob('*.mp3')):
        match=re.fullmatch(folder+r'-(\d+)\.mp3',source.name)
        if not match or int(match[1]) not in texts:raise ValueError(f'Unknown recording: {source.name}')
        text=texts[int(match[1])];raw=source.read_bytes()
        if len(raw)<1000:raise ValueError(f'Empty recording: {source.name}')
        sha=hashlib.sha256(raw).hexdigest();name=sha+'.mp3'
        shutil.copyfile(source,output/name)
        entries[hashlib.sha256(text.encode()).hexdigest()]={'text':text,'file':name,'source':source.name,'sha256':sha,'provider':'Звукограм','speaker':'Девочка Таня' if folder=='sofia' else 'Мальчик Петя'}
    manifest['voices'][voice]=entries
    print(f'{voice}: {len(entries)} imported; {len(texts)-len(entries)} use previous recordings')
temporary=output/'overrides.tmp'
temporary.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf-8')
temporary.replace(output/'overrides.json')
