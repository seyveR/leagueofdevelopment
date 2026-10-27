"""No DB fixtures: run with python -m unittest tests.test_audio_overrides."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from app import audio

class ImportedAudio(unittest.TestCase):
    def test_exact_text_voice_override_and_missing_file_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            previous=audio.AUDIO_ROOT;audio.AUDIO_ROOT=Path(directory)
            try:
                text='Проверочная инструкция';sha='a'*64
                for voice in ['ru-sofia','ru-lev']:
                    key=audio.cache_key(text,voice,sha)
                    (audio.AUDIO_ROOT/(key+'.wav')).write_bytes(b'old')
                clips={audio.cache_key(text,v,sha):text for v in ['ru-sofia','ru-lev']}
                (audio.AUDIO_ROOT/'manifest.json').write_text(json.dumps({'model_sha256':sha,'clips':clips}))
                name='b'*64+'.mp3';(audio.AUDIO_ROOT/name).write_bytes(b'new')
                text_key=hashlib.sha256(text.encode()).hexdigest()
                (audio.AUDIO_ROOT/'overrides.json').write_text(json.dumps({'voices':{'ru-sofia':{text_key:{'text':text,'file':name}}}}))
                self.assertTrue(audio.clip(text,'ru-sofia').endswith('.mp3'))
                self.assertEqual(audio.audio_file(name).media_type,'audio/mpeg')
                self.assertTrue(audio.clip(text,'ru-lev').endswith('.wav'))
                self.assertIsNone(audio.clip(text+' новый','ru-sofia'))
                (audio.AUDIO_ROOT/name).unlink()
                self.assertTrue(audio.clip(text,'ru-sofia').endswith('.wav'))
                (audio.AUDIO_ROOT/'overrides.json').write_text('broken')
                self.assertTrue(audio.clip(text,'ru-sofia').endswith('.wav'))
            finally:audio.AUDIO_ROOT=previous
