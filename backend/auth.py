# backend/auth.py
from __future__ import annotations
import os, time, typing as t
from fastapi import Depends, HTTPException, status, Header
from pydantic import BaseModel
import jwt  # PyJWT

# Env:
# AUTH_JWT_SECRET=devsecret
# DEV_NO_AUTH=1   -> disables auth (everything runs as user "demo")
JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "devsecret")
JWT_ALG = "HS256"
DEV_NO_AUTH = 1

class User(BaseModel):
    user_id: str
    email: str | None = None

def get_current_user(authorization: t.Optional[str] = Header(None)) -> User:
    if DEV_NO_AUTH:
        return User(user_id="demo", email="demo@example.com")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        # expected claims: { "sub": "<user_id>", "email": "..." }
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Missing sub")
        # (optional) exp check – PyJWT already validates exp if present
        return User(user_id=sub, email=payload.get("email"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
