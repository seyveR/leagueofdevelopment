from fastapi.testclient import TestClient
from app.main import app
from .conftest import register
from .test_api import create_child

def test_account_settings_inheritance_overrides_and_ownership(client):
    register(client);child=create_child(client)
    defaults=client.get('/api/settings').json()['settings']
    assert defaults['speech'] is False and defaults['character'] is True
    settings={**defaults,'speech':True,'autoplay':True,'voice':'ru-lev','character':False,'text_size':'large'}
    assert client.put('/api/settings',json=settings).status_code==200
    inherited=client.get('/api/settings',params={'child_id':child['id']}).json()
    assert inherited['settings']==settings and not inherited['overridden']
    changed=client.put('/api/settings',params={'child_id':child['id']},json={**settings,'speech':False,'character':True}).json()
    assert changed['settings']['autoplay'] is False and changed['overridden']
    assert client.get('/api/settings').json()['settings']==settings
    other=TestClient(app);register(other,'settings-other@example.com')
    assert other.get('/api/settings',params={'child_id':child['id']}).status_code==404
    assert client.put('/api/settings',json={**settings,'rate':9}).status_code==422
    assert client.delete('/api/settings',params={'child_id':child['id']}).json()['settings']==settings

def test_audio_missing_is_honest_and_no_path_traversal(client):
    register(client)
    catalog=client.get('/api/audio/catalog').json()
    assert len(catalog['voices'])==2
    assert {v['character'] for v in catalog['voices']}=={'lev','sofia'}
    response=client.get('/api/audio/resolve',params={'text':'Новая инструкция','voice':'ru-lev'}).json()
    assert response['url'] is None
    assert client.get('/api/audio/files/not-a-hash.wav').status_code==404
    assert client.get('/api/audio/resolve',params={'text':'Текст','voice':'unknown'}).status_code==422
