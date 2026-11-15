import json
import pytest
from fastapi.testclient import TestClient
from app.main import app, rates
from app.config import settings
from app.storage import storage

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'model_backend', 'demo')
    monkeypatch.setattr(settings, 'database_path', str(tmp_path/'test.sqlite3'))
    monkeypatch.setattr(settings, 'api_key', '')
    monkeypatch.setattr(storage, 'redis', None)
    storage.memory.clear()
    rates.clear()
    with TestClient(app) as client:
        yield client

def product(client):
    return client.get('/api/products').json()['products'][0]

def test_validation(client):
    p=product(client);p['price']=-1
    assert client.post('/api/extract/selling-points',json=p).status_code==422

def test_cache_invalidation(client):
    p=product(client)
    key=storage.key(__import__('app.models',fromlist=['Product']).Product(**p))
    result=client.post('/api/extract/selling-points',json=p)
    assert result.status_code==200
    assert 3<=len(result.json()['selling_points'])<=5
    p['price']+=1
    assert key!=storage.key(__import__('app.models',fromlist=['Product']).Product(**p))

@pytest.mark.parametrize('stage',['opening','intro','promote','close'])
@pytest.mark.parametrize('style',['passionate','professional','humorous'])
def test_stream_and_feedback(client,stage,style):
    response=client.post('/api/generate/script',json={'product':product(client),'script_type':stage,'style':style})
    assert response.status_code==200
    events=[json.loads(s[6:]) for s in response.text.strip().split('\n\n')]
    assert events[0]['type']=='selling_points'
    assert events[-1]['type']=='done'
    result=events[-1]['data']
    assert result['content']==''.join(e['data'] for e in events if e['type']=='token')
    assert client.post('/api/feedback',json={'generation_id':result['generation_id'],'rating':1}).status_code==200

def test_reply_and_nonstream(client):
    p=product(client)
    assert client.post('/api/interact/reply',json={'product':p,'question':'多少钱'}).json()['intent']=='price'
    assert client.post('/api/generate/script',json={'product':p,'script_type':'intro','stream':False}).json()['content']

def test_auth_rate_limit(client,monkeypatch):
    monkeypatch.setattr(settings,'api_key','test-secret')
    assert client.get('/api/products').status_code==401
    for _ in range(60):
        assert client.get('/api/products',headers={'X-API-Key':'test-secret'}).status_code==200
    assert client.get('/api/products',headers={'X-API-Key':'test-secret'}).status_code==429

def test_model_failure_not_demo(client,monkeypatch):
    import app.main as main
    async def broken(*args):
        raise TimeoutError('upstream')
    monkeypatch.setattr(main,'selling_points',broken)
    r=client.post('/api/generate/script',json={'product':product(client),'script_type':'intro'})
    assert r.status_code==504

def test_stream_error(client,monkeypatch):
    import app.main as main
    async def broken(*args):
        yield 'partial'
        raise RuntimeError('secret upstream error')
    monkeypatch.setattr(main,'script_stream',broken)
    r=client.post('/api/generate/script',json={'product':product(client),'script_type':'intro'})
    assert '"type": "error"' in r.text
    assert '"type": "done"' not in r.text
    assert 'secret upstream error' not in r.text
