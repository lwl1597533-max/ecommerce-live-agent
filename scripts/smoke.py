"""Check the running app with a synthetic product; never print credentials."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import httpx
from app.config import settings

with httpx.Client(base_url='http://127.0.0.1:8000',timeout=180,headers={'X-API-Key':settings.api_key}) as c:
    print('health:',c.get('/health').json())
    print('ready:',c.get('/ready').status_code)
    p=c.get('/api/products').json()['products'][0]
    r=c.post('/api/extract/selling-points',json=p)
    print('selling_points:',r.status_code)
    r.raise_for_status()
    print('point_count:',len(r.json()['selling_points']))
    r=c.post('/api/generate/script',json={'product':p,'script_type':'intro','style':'professional','duration_seconds':30,'stream':True})
    r.raise_for_status()
    events=[json.loads(s[6:]) for s in r.text.strip().split('\n\n')]
    print('stream_events:',len(events),'last_event:',events[-1]['type'])
    assert events[-1]['type']=='done', 'Stream failed'
    result=events[-1]['data']
    print('generated_chars:',result['word_count'],'backend:',result['backend'])
    r=c.post('/api/interact/reply',json={'product':p,'question':'这款多少钱？'})
    print('interaction:',r.status_code)
    r.raise_for_status()
    print('intent:',r.json()['intent'])
    assert r.json()['intent']=='price'
    print('SMOKE PASS')
