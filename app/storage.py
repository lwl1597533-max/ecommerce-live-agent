import asyncio
import hashlib
import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from redis.asyncio import Redis
from app.config import settings

class Storage:
    def __init__(self):
        self.memory = {}
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1) if settings.redis_url else None

    def init(self):
        Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(settings.database_path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS generations (id TEXT PRIMARY KEY, created REAL, kind TEXT, version TEXT, backend TEXT, request TEXT, output TEXT, elapsed REAL, rating INTEGER)')

    def key(self, product):
        payload = [product.model_dump(), settings.prompt_version, settings.model_name, settings.model_backend]
        return 'sp:' + hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    async def get(self, key):
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    return json.loads(value)
            except Exception:
                logging.warning('Redis unavailable; using bounded in-process cache')
        entry = self.memory.get(key)
        return entry[1] if entry and entry[0] > time.time() else None

    async def set(self, key, value):
        if len(self.memory) >= 1000:
            self.memory.pop(next(iter(self.memory)))
        self.memory[key] = (time.time() + settings.cache_ttl_seconds, value)
        if self.redis:
            try:
                await self.redis.setex(key, settings.cache_ttl_seconds, json.dumps(value, ensure_ascii=False))
            except Exception:
                logging.warning('Redis write failed; using in-process cache')

    async def log(self, kind, request, output, elapsed):
        identifier = str(uuid.uuid4())
        def write():
            with sqlite3.connect(settings.database_path) as db:
                db.execute('INSERT INTO generations VALUES (?,?,?,?,?,?,?,?,NULL)', (identifier, time.time(), kind, settings.prompt_version, settings.model_backend, json.dumps(request, ensure_ascii=False), json.dumps(output, ensure_ascii=False), elapsed))
        await asyncio.to_thread(write)
        return identifier

    async def feedback(self, identifier, rating):
        def write():
            with sqlite3.connect(settings.database_path) as db:
                return db.execute('UPDATE generations SET rating=? WHERE id=?', (rating, identifier)).rowcount
        return await asyncio.to_thread(write)

storage = Storage()
