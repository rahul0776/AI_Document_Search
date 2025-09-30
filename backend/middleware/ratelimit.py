import time
from collections import deque
from fastapi import Request, HTTPException

WINDOW_S = 60

class InprocLimiter:
    def __init__(self, max_calls_per_min: int):
        self.max = max_calls_per_min
        self.hits = {}  # key -> deque[timestamps]

    def check(self, key: str):
        now = time.time()
        dq = self.hits.setdefault(key, deque())
        while dq and now - dq[0] > WINDOW_S:
            dq.popleft()
        if len(dq) >= self.max:
            raise HTTPException(status_code=429, detail="Too many requests, slow down")
        dq.append(now)

limiter = InprocLimiter(max_calls_per_min=12)

async def limit_uploads(request: Request):
    ip = request.client.host if request.client else "anon"
    limiter.check(f"upload:{ip}")

async def limit_chat(request: Request):
    ip = request.client.host if request.client else "anon"
    limiter.check(f"chat:{ip}")
