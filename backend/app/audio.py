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
    if not re.fullmatch(r'[a-f0-9]{64}\.wav',filename):raise HTTPException(404)
    path=AUDIO_ROOT/filename
    if not path.is_file():raise HTTPException(404)
    return FileResponse(path,media_type='audio/wav')

