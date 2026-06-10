import threading
import time
from collections import deque
from fastapi import Request, HTTPException

WINDOW_S = 60

class InprocLimiter:
    def __init__(self, max_calls_per_min: int):
        self.max = max_calls_per_min
        self.hits = {}  # key -> deque[timestamps]
        self._lock = threading.Lock()

    def check(self, key: str):
        now = time.time()
        with self._lock:
            dq = self.hits.setdefault(key, deque())
            while dq and now - dq[0] > WINDOW_S:
                dq.popleft()
            if len(dq) >= self.max:
                raise HTTPException(status_code=429, detail="Too many requests, slow down")
            dq.append(now)

chat_limiter = InprocLimiter(max_calls_per_min=12)
upload_limiter = InprocLimiter(max_calls_per_min=5)

def _client_key(request: Request) -> str:
    """Real client IP. Behind a proxy (Render/Vercel), request.client.host is the
    proxy's IP, so prefer the first hop in X-Forwarded-For."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "anon"

async def limit_uploads(request: Request):
    upload_limiter.check(f"upload:{_client_key(request)}")

async def limit_chat(request: Request):
    chat_limiter.check(f"chat:{_client_key(request)}")
