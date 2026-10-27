import hashlib,json,os
from pathlib import Path

AUDIO_ROOT=Path(os.getenv('AUDIO_ROOT','/data/audio'))
MODEL='silero-v5-cis-base-nostress'
VOICES=[{'id':'ru-sofia','name':'София · русский женский','speaker':'ru_zara','character':'sofia','model':MODEL,'license':'MIT (LICENSE_CIS)'},
        {'id':'ru-lev','name':'Лев · русский мужской','speaker':'ru_bogdan','character':'lev','model':MODEL,'license':'MIT (LICENSE_CIS)'}]
SAMPLE='Привет! Сейчас мы выполним несколько заданий. Можно не спешить. Если нужно, повтори инструкцию.'
INSTRUCTION='Выберите один ответ на каждое задание. В заданиях на память сначала запомните материал, затем нажмите «Скрыть и ответить». Ответ сохраняется после нажатия «Сохранить и дальше». Можно выйти и продолжить позже.'
MEMORY='Запомните материал. Затем нажмите Скрыть и ответить.'

def cache_key(text,voice,model_sha):
    raw=json.dumps({'text':text,'language':'ru-RU','voice':voice,'model':MODEL,'model_sha256':model_sha},sort_keys=True,ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()



