import asyncio
import hmac
import json
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from openai import APITimeoutError
from app.config import settings
from app.models import Product, ScriptRequest, InteractionRequest, Feedback
from app.storage import storage
from app.chains import selling_points, script_stream, interact, ModelUnavailableError

ROOT = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app):
    storage.init()
    yield
    if storage.redis:
        await storage.redis.aclose()

app = FastAPI(title='电商直播文案生成 Agent', version='1.0.0', lifespan=lifespan)
rates = defaultdict(deque)

@app.middleware('http')
async def access(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        if settings.api_key and not hmac.compare_digest(request.headers.get('x-api-key',''), settings.api_key):
            return JSONResponse({'detail':'API Key 无效'}, status_code=401)
        now = time.monotonic()
        host = request.client.host if request.client else 'unknown'
        if len(rates) > 10000:
            for key in list(rates):
                if not rates[key] or now-rates[key][-1] > 60:
                    del rates[key]
        queue = rates[host]
        while queue and now-queue[0] > 60:
            queue.popleft()
        if len(queue) >= 60:
            return JSONResponse({'detail':'请求过于频繁，请稍后重试'}, status_code=429, headers={'Retry-After':'60'})
        queue.append(now)
    return await call_next(request)

def fail(exc):
    logging.exception('Generation failed')
    if isinstance(exc, ModelUnavailableError):
        return HTTPException(502, '上游模型服务返回“模型请求失败，请稍后重试或更换模型”。请在服务商控制台确认该模型可用，或修改 .env 中的 MODEL_NAME 后重启服务。')
    timeout = isinstance(exc, (APITimeoutError, asyncio.TimeoutError))
    return HTTPException(504 if timeout else 502, '模型请求超时' if timeout else '生成失败，请检查模型配置和服务日志')

@app.get('/')
async def index():
    return FileResponse(ROOT / 'static/index.html')

@app.get('/health')
async def health():
    return {'status':'ok', 'backend':settings.model_backend, 'model':settings.model_name, 'prompt_version':settings.prompt_version, 'cache':'redis_with_memory_fallback' if storage.redis else 'memory'}

@app.get('/ready')
async def ready():
    if settings.model_backend == 'demo':
        return {'ready':True, 'backend':'demo', 'real_model':False}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(settings.vllm_base_url.rstrip('/')+'/models', headers={'Authorization':f'Bearer {settings.vllm_api_key}'})
            response.raise_for_status()
            names = [m['id'] for m in response.json().get('data', [])]
            if settings.model_name not in names:
                raise ValueError('Configured model unavailable')
        return {'ready':True, 'real_model':True}
    except Exception:
        return JSONResponse({'ready':False, 'detail':'无法确认模型可用，请检查服务地址、密钥和模型名'}, status_code=503)

@app.get('/api/products')
async def products():
    return json.loads((ROOT/'data/mock_products.json').read_text(encoding='utf-8'))

@app.post('/api/extract/selling-points')
async def extract(product: Product):
    try:
        return await selling_points(product)
    except Exception as exc:
        raise fail(exc)

def event(kind, data):
    return 'data: ' + json.dumps({'type':kind, 'data':data}, ensure_ascii=False) + '\n\n'

@app.post('/api/generate/script')
async def generate(req: ScriptRequest, request: Request):
    start = time.monotonic()
    try:
        points = await selling_points(req.product)
    except Exception as exc:
        raise fail(exc)
    async def complete(content):
        result = {'content':content, 'script_type':req.script_type, 'style':req.style, 'word_count':len(content), 'estimated_duration_seconds':round(len(content)/4), 'elapsed_seconds':round(time.monotonic()-start, 3), 'backend':settings.model_backend, 'duration_in_range':req.duration_seconds*3.2 <= len(content) <= req.duration_seconds*4.8}
        result['generation_id'] = await storage.log('script', req.model_dump(), result, result['elapsed_seconds'])
        return result
    if not req.stream:
        try:
            chunks = [token async for token in script_stream(req, points)]
            return await complete(''.join(chunks))
        except Exception as exc:
            raise fail(exc)
    async def events():
        yield event('selling_points', points.model_dump())
        chunks = []
        try:
            async for token in script_stream(req, points):
                if await request.is_disconnected():
                    return
                chunks.append(token)
                yield event('token', token)
            yield event('done', await complete(''.join(chunks)))
        except Exception:
            logging.exception('Stream failed')
            yield event('error', {'message':'生成中断，请检查模型服务后重试'})
    return StreamingResponse(events(), media_type='text/event-stream', headers={'Cache-Control':'no-cache', 'X-Accel-Buffering':'no'})

@app.post('/api/interact/reply')
async def reply(req: InteractionRequest):
    start = time.monotonic()
    try:
        result = (await interact(req)).model_dump()
        result['generation_id'] = await storage.log('interaction', req.model_dump(), result, time.monotonic()-start)
        result['backend'] = settings.model_backend
        return result
    except Exception as exc:
        raise fail(exc)

@app.post('/api/feedback')
async def feedback(req: Feedback):
    if not await storage.feedback(req.generation_id, req.rating):
        raise HTTPException(404, '生成记录不存在')
    return {'saved':True}
