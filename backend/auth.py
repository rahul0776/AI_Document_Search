# backend/auth.py
from __future__ import annotations
import os, time, typing as t
from fastapi import HTTPException, Header, status
from pydantic import BaseModel
import jwt  # PyJWT

JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "devsecret")
JWT_ALG = "HS256"
JWT_ISS = os.getenv("AUTH_JWT_ISS", "rag-app")
DEV_NO_AUTH = os.getenv("DEV_NO_AUTH", "0") == "1"

class User(BaseModel):
    user_id: str
    email: str | None = None

def issue_token(user_id: str, email: str | None = None, hours: int = 24) -> str:
    now = int(time.time())
    payload = {
        "iss": JWT_ISS,
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + hours * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def get_current_user(authorization: t.Optional[str] = Header(None)) -> User:
    if DEV_NO_AUTH:
        return User(user_id="demo", email="demo@example.com")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG], options={"require": ["iss", "sub", "exp"]})
        if payload.get("iss") != JWT_ISS:
            raise ValueError("Bad issuer")
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Missing sub")
        return User(user_id=sub, email=payload.get("email"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
