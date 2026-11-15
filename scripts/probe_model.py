import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import httpx
from app.config import settings

with httpx.Client(timeout=90) as client:
    response=client.post(settings.vllm_base_url.rstrip('/')+'/chat/completions',headers={'Authorization':f'Bearer {settings.vllm_api_key}'},json={'model':settings.model_name,'messages':[{'role':'user','content':'请只回复：你好'}],'max_tokens':64})
    print('status:',response.status_code,flush=True)
    if response.status_code==200:
        data=response.json()
        print('response:',data.get('choices',[{}])[0].get('message',{}).get('content'),flush=True)
    else:
        print('Upstream rejected request; credentials withheld',flush=True)
