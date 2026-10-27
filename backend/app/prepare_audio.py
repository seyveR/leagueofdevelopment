"""Offline CLI. Explicit local model and checksum; never called by API startup."""
import argparse,hashlib,json,os,wave
from pathlib import Path
from .audio import AUDIO_ROOT,VOICES,SAMPLE,INSTRUCTION,MEMORY,cache_key
from .content import TASKS

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',required=True);parser.add_argument('--expected-sha256',required=True);args=parser.parse_args()
    path=Path(args.model);sha=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
    if sha!=args.expected_sha256:raise SystemExit('Контрольная сумма модели не совпала')
    # torch is an OPTIONAL offline tool dependency, never an API dependency.
    import torch
    torch.set_num_threads(2)
    model=torch.package.PackageImporter(str(path)).load_pickle('tts_models','model')
    texts={SAMPLE,INSTRUCTION,MEMORY,'Готово. Ответы сохранены. Можно посмотреть результаты.'}
    texts.update(t['prompt'] for t in TASKS)
    try:
        from .age_tasks import SCENARIOS
        texts.update(t['prompt'] for scenario in SCENARIOS.values() for t in scenario['tasks'])
    except ImportError:pass
    AUDIO_ROOT.mkdir(parents=True,exist_ok=True);clips={}
    for voice in VOICES:
        if voice['speaker'] not in model.speakers:raise SystemExit(f"Модель не содержит {voice['speaker']}")
        for text in sorted(texts):
            key=cache_key(text,voice['id'],sha);target=AUDIO_ROOT/f'{key}.wav'
            if not target.exists():
                samples=model.apply_tts(text=text,speaker=voice['speaker'],sample_rate=24000)
                pcm=(samples.clamp(-1,1)*32767).to(torch.int16).numpy().tobytes()
                temporary=target.with_suffix('.tmp')
                with wave.open(str(temporary),'wb') as out:out.setnchannels(1);out.setsampwidth(2);out.setframerate(24000);out.writeframes(pcm)
                os.replace(temporary,target)
            clips[key]=text
    temporary=AUDIO_ROOT/'manifest.tmp'
    temporary.write_text(json.dumps({'model_sha256':sha,'model_version':'v5_cis_base_nostress','voices':VOICES,'clips':clips},ensure_ascii=False,indent=2),'utf-8')
    os.replace(temporary,AUDIO_ROOT/'manifest.json');print(f'Prepared {len(clips)} clips; model sha256={sha}')
if __name__=='__main__':main()
