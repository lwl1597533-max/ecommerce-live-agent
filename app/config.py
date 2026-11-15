from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    model_backend: Literal['demo', 'openai'] = 'demo'
    model_name: str = 'Qwen/Qwen-7B-Chat'
    vllm_base_url: str = 'http://127.0.0.1:8001/v1'
    vllm_api_key: str = 'EMPTY'
    redis_url: str = ''
    api_key: str = ''
    prompt_version: str = 'v1'
    request_timeout: float = 60
    cache_ttl_seconds: int = 86400
    database_path: str = 'runtime/generations.sqlite3'

settings = Settings()
