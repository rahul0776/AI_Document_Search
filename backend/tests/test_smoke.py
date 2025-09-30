# backend/tests/test_smoke.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

@pytest.mark.asyncio
async def test_ask_empty_index():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/ask", json={"question": "hi", "top_k": 3})
        assert resp.status_code == 200
        assert resp.json()["results"] == []
