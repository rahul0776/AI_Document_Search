# backend/services/embeddings.py
import hashlib, json, threading
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI

class Settings(BaseSettings):
    openai_api_key: str
    embed_model: str = "text-embedding-3-small"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

_settings = Settings()
_client = OpenAI(api_key=_settings.openai_api_key)

CACHE = Path("./data/embed_cache.json")
CACHE.parent.mkdir(parents=True, exist_ok=True)
_cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
_cache_lock = threading.Lock()

def _key(text: str, model: str) -> str:
    return hashlib.sha256((model + "||" + text).encode("utf-8")).hexdigest()

def embed_texts(texts: List[str], model: str | None = None) -> List[List[float]]:
    model = model or _settings.embed_model
    outs, todo_idx, todo_payload = [], [], []
    with _cache_lock:
        for i, t in enumerate(texts):
            k = _key(t, model)
            if k in _cache:
                outs.append(_cache[k])
            else:
                outs.append(None); todo_idx.append(i); todo_payload.append(t)

    if todo_payload:
        resp = _client.embeddings.create(model=model, input=todo_payload)
        with _cache_lock:
            for i, d in zip(todo_idx, resp.data):
                emb = d.embedding
                _cache[_key(texts[i], model)] = emb
                outs[i] = emb
            CACHE.write_text(json.dumps(_cache), encoding="utf-8")
    return outs
