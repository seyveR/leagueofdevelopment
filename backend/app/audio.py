"""Only prepared, non-personal instructions. No model loads in the HTTP process."""
import hashlib,json,os,re
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException,Query
from fastapi.responses import FileResponse
from .security import current_user

from .audio_content import AUDIO_ROOT,MODEL,VOICES,SAMPLE,INSTRUCTION,MEMORY,cache_key

def manifest():
    try:return json.loads((AUDIO_ROOT/'manifest.json').read_text('utf-8'))
    except (OSError,ValueError):return {'clips':{},'model_sha256':None}

def clip(text,voice):
    # Imported recordings override only an exact voice/text pair. Other clips keep Silero.
    try:
        overrides=json.loads((AUDIO_ROOT/'overrides.json').read_text('utf-8'))
        key=hashlib.sha256(text.encode('utf-8')).hexdigest()
        entry=overrides.get('voices',{}).get(voice,{}).get(key,{})
        filename=entry.get('file','')
        if entry.get('text')==text and re.fullmatch(r'[a-f0-9]{64}\.mp3',filename) and (AUDIO_ROOT/filename).is_file():
            return f'/api/audio/files/{filename}'
    except (OSError,ValueError,AttributeError,TypeError):pass
    data=manifest();sha=data.get('model_sha256')
    if not sha:return None
    key=cache_key(text,voice,sha)
    return f'/api/audio/files/{key}.wav' if data.get('clips',{}).get(key)==text and (AUDIO_ROOT/f'{key}.wav').is_file() else None

router=APIRouter(prefix='/api/audio',tags=['Озвучка'])
@router.get('/catalog')
def catalog(user=Depends(current_user)):
    return {'voices':[{**v,'sample_url':clip(SAMPLE,v['id'])} for v in VOICES],'model_sha256':manifest().get('model_sha256'),'preparation_required':not bool(manifest().get('model_sha256'))}
@router.get('/resolve')
def resolve(text:str=Query(max_length=1500),voice:str='ru-sofia',user=Depends(current_user)):
    if voice not in [v['id'] for v in VOICES]:raise HTTPException(422,'Неизвестный голос')
    return {'url':clip(text,voice),'message':'Запись не подготовлена. Используйте текстовую инструкцию.'}
@router.get('/files/{filename}')
def audio_file(filename:str):
    if not re.fullmatch(r'[a-f0-9]{64}\.(wav|mp3)',filename):raise HTTPException(404)
    path=AUDIO_ROOT/filename
    if not path.is_file():raise HTTPException(404)
    return FileResponse(path,media_type='audio/mpeg' if filename.endswith('.mp3') else 'audio/wav')

