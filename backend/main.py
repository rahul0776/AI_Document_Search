# backend/main.py
from __future__ import annotations

import json
import uuid
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import os
import sys
import tempfile

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from pydantic_settings import BaseSettings, SettingsConfigDict
from sse_starlette.sse import EventSourceResponse

# ── Auth/user
from auth import get_current_user, User, issue_token

# ── Registries/services
from services.index_registry import IndexRegistry
from ingestion.pdf_text import extract_pdf_text
from services.embeddings import embed_texts, Settings as EmbSettings
from models.schemas import UploadResponse, AskRequest, AskResult, ChatRequest
from services.rag import ask_llm, build_messages, stream_openai, citations_from
from services.docmeta import DocMetaStore
from services.rerank import mmr_rerank
from services.quality import dedupe_hits, cap_per_doc
from services.telemetry import log_event
from middleware.ratelimit import limit_chat

log = logging.getLogger("uvicorn.error")

# ─────────────────── Settings ───────────────────
class Settings(BaseSettings):
    frontend_origin: str = "http://localhost:3000"
    index_dir: str = "./data/index"
    upload_dir: str = "./data/uploads"
    max_pdf_mb: int = 40
    max_pages: int = 2000
    openai_timeout_s: int = 45
    openai_retries: int = 3
    top_k_default: int = 5
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
emb_settings = EmbSettings()

# During tests: isolate index directory
if ("pytest" in sys.modules) or os.getenv("PYTEST_CURRENT_TEST"):
    test_index_dir = Path(tempfile.gettempdir()) / "rag_test_index"
    shutil.rmtree(test_index_dir, ignore_errors=True)
    settings.index_dir = str(test_index_dir)

# ─────────────────── FastAPI app (MUST be before any decorators) ───────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INDEXES = IndexRegistry(settings.index_dir)
app.mount("/files", StaticFiles(directory=settings.upload_dir), name="files")

# ─────────────────── Helpers ───────────────────
def meta_for(user: User) -> DocMetaStore:
    """Per-user metadata store: uploads/<user_id>/docs.json"""
    udir = Path(settings.upload_dir) / user.user_id
    return DocMetaStore(str(udir))

def uploads_dir_for(user: User) -> Path:
    udir = Path(settings.upload_dir) / user.user_id
    udir.mkdir(parents=True, exist_ok=True)
    return udir

def _filter_hits_by_doc(hits: List[Dict[str, Any]], doc_id: Optional[str], top_k: int) -> List[Dict[str, Any]]:
    if doc_id:
        hits = [h for h in hits if h.get("doc_id") == doc_id]
    return hits[:top_k]

@app.exception_handler(Exception)
async def all_errors(_, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"ok": False, "code": "SERVER_ERROR", "message": "Something went wrong. Try again."},
    )

@app.exception_handler(RequestValidationError)
async def bad_request(_, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"ok": False, "code": "BAD_REQUEST", "errors": exc.errors()})

# ─────────────────── Auth (dev) ───────────────────
@app.post("/auth/dev_login")
def dev_login(body: Dict[str, Any]):
    """
    Dev-only endpoint to mint a JWT for quick testing.
    POST {"user_id": "demo", "email": "demo@example.com"}
    """
    if body is None:
        raise HTTPException(status_code=400, detail="JSON body required")
    user_id = (body.get("user_id") or "demo").strip()
    email = (body.get("email") or None)
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    token = issue_token(user_id=user_id, email=email, hours=24)
    return {"token": token, "user": {"user_id": user_id, "email": email}}

@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user_id": user.user_id, "email": user.email}

# ─────────────────── Health ───────────────────
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/hello")
def hello():
    return {"message": "Backend is running!"}

# ───────────── Upload ─────────────
@app.post("/upload", response_model=UploadResponse)
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Some servers provide size; if available, enforce limit
    if getattr(file, "size", None) and settings.max_pdf_mb:
        if file.size > settings.max_pdf_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"PDF too large (>{settings.max_pdf_mb}MB)")

    doc_id = str(uuid.uuid4())
    updir = uploads_dir_for(user)
    dest = updir / f"{doc_id}.pdf"

    log.info(f"[UPLOAD] u={user.user_id} file={file.filename} -> {dest}")
    try:
        try:
            file.file.seek(0)
        except Exception:
            pass
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except Exception:
        log.exception("[UPLOAD] write failed")
        raise HTTPException(status_code=500, detail="Failed to save file")

    META = meta_for(user)
    try:
        META.add(doc_id, file.filename, pages=0)  # provisional so it appears in list
    except Exception:
        log.exception(f"[META] provisional add failed for {doc_id}")

    def _index_pdf():
        try:
            log.info(f"[INDEX] begin u={user.user_id} doc={doc_id}")
            pages = extract_pdf_text(str(dest))

            if settings.max_pages and len(pages) > settings.max_pages:
                log.warning(f"[INDEX] u={user.user_id} doc={doc_id} too many pages ({len(pages)})")
                return 0

            from ingestion.pdf_text import guess_title
            from ingestion.chunker import smart_chunk_pages

            title = guess_title(pages) or file.filename.rsplit(".", 1)[0]
            try:
                META.add(doc_id, file.filename, pages=len(pages), title=title)
            except Exception:
                pass

            chunks = list(smart_chunk_pages(pages, target_chars=900, overlap_chars=120))
            if not chunks:
                log.warning(f"[INDEX] no chunks for {doc_id}")
                return 0

            texts = [c["text"] for c in chunks]
            embs = embed_texts(texts, model=emb_settings.embed_model)
            metas = [{"text": c["text"][:1000], "page": c["page"], "doc_id": doc_id, "title": title} for c in chunks]
            INDEXES.for_user(user.user_id).upsert(embs, metas)
            log.info(f"[INDEX] done u={user.user_id} doc={doc_id} chunks={len(chunks)}")
            return len(chunks)
        except Exception:
            log.exception(f"[INDEX] error u={user.user_id} doc={doc_id}")
            return 0

    background_tasks.add_task(_index_pdf)
    return {"doc_id": doc_id, "chunks": 0}

# ───────────── Ask (retrieve only) ─────────────
@app.post("/ask", response_model=AskResult)
async def ask(payload: AskRequest, user: User = Depends(get_current_user)):
    INDEX = INDEXES.for_user(user.user_id)

    if hasattr(INDEX, "is_empty") and INDEX.is_empty():
        return {"results": []}

    doc_id = getattr(payload, "doc_id", None)
    if doc_id and hasattr(INDEX, "count") and INDEX.count(doc_id) == 0:
        return {"results": []}

    qemb = embed_texts([payload.question])[0]
    hits = INDEX.search(qemb, k=max(50, payload.top_k * 3))
    hits = _filter_hits_by_doc(hits, doc_id, 50)
    hits = dedupe_hits(hits)
    hits = cap_per_doc(hits, per_doc=int(os.getenv("MAX_CHUNKS_PER_DOC", "3")))
    hits = mmr_rerank(payload.question, hits, top_k=payload.top_k)

    try:
        log_event("ask", {"user_id": user.user_id, "q": payload.question, "scope": doc_id or "ALL", "n": len(hits)})
    except Exception:
        pass

    for h in hits:
        h["text"] = (h.get("text") or "")[:400]
    return {"results": hits}

# ───────────── Chat (non-streaming) ─────────────
@app.post("/chat", dependencies=[Depends(limit_chat)])
async def chat(payload: ChatRequest, user: User = Depends(get_current_user)):
    INDEX = INDEXES.for_user(user.user_id)

    if hasattr(INDEX, "is_empty") and INDEX.is_empty():
        return {"answer": "Please upload a PDF first. I don't have any documents to search yet.", "citations": []}

    doc_id = getattr(payload, "doc_id", None)
    if doc_id and hasattr(INDEX, "count") and INDEX.count(doc_id) == 0:
        return {"answer": "Still indexing that PDF. Try again in a few seconds.", "citations": []}

    qemb = embed_texts([payload.question])[0]
    hits = INDEX.search(qemb, k=max(50, payload.top_k * 3))
    hits = _filter_hits_by_doc(hits, doc_id, 50)
    hits = dedupe_hits(hits)
    hits = cap_per_doc(hits, per_doc=int(os.getenv("MAX_CHUNKS_PER_DOC", "3")))
    hits = mmr_rerank(payload.question, hits, top_k=payload.top_k)

    if not hits or hits[0].get("score", 0) < 0.05:
        return {"answer": "I don't know. I couldn't find enough supporting context.", "citations": []}

    try:
        log_event("chat", {"user_id": user.user_id, "q": payload.question, "scope": doc_id or "ALL", "n": len(hits)})
    except Exception:
        pass

    return ask_llm(payload.question, hits)

# ───────────── Chat (streaming SSE) ─────────────
@app.get("/chat_stream", dependencies=[Depends(limit_chat)])
async def chat_stream(
    request: Request,
    question: str,
    top_k: int = 5,
    doc_id: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    INDEX = INDEXES.for_user(user.user_id)

    if hasattr(INDEX, "is_empty") and INDEX.is_empty():
        async def no_docs():
            yield {"event": "token", "data": "Please upload a PDF first. I don't have any documents to search yet."}
            yield {"event": "done", "data": '{"citations": []}'}
        return EventSourceResponse(no_docs())

    if doc_id and hasattr(INDEX, "count") and INDEX.count(doc_id) == 0:
        async def indexing_stream():
            yield {"event": "token", "data": "Still indexing that PDF. "}
            yield {"event": "token", "data": "Try again in a few seconds."}
            yield {"event": "done", "data": '{"citations": []}'}
        return EventSourceResponse(indexing_stream())

    qemb = embed_texts([question])[0]
    hits = INDEX.search(qemb, k=max(50, top_k * 3))
    hits = _filter_hits_by_doc(hits, doc_id, 50)
    hits = dedupe_hits(hits)
    hits = cap_per_doc(hits, per_doc=int(os.getenv("MAX_CHUNKS_PER_DOC", "3")))
    hits = mmr_rerank(question, hits, top_k=top_k)

    try:
        log_event("chat_stream", {"user_id": user.user_id, "q": question, "scope": doc_id or "ALL", "n": len(hits)})
    except Exception:
        pass

    if not hits or hits[0].get("score", 0) < 0.05:
        async def no_context_stream():
            yield {"event": "token", "data": "I don't know. I couldn't find enough supporting context."}
            yield {"event": "done", "data": '{"citations": []}'}
        return EventSourceResponse(no_context_stream())

    messages = build_messages(question, hits)
    cits_json = json.dumps({"citations": citations_from(hits)})

    async def event_generator():
        for piece in stream_openai(messages):
            if await request.is_disconnected():
                break
            yield {"event": "token", "data": piece}
        yield {"event": "done", "data": cits_json}

    return EventSourceResponse(event_generator())

# ───────────── Documents: list & delete ─────────────
@app.get("/documents")
def list_docs(user: User = Depends(get_current_user)):
    updir = uploads_dir_for(user)
    META = meta_for(user)

    try:
        meta_list = META.all() or []
    except Exception:
        meta_list = []

    meta_map: Dict[str, Dict[str, Any]] = {m["doc_id"]: m for m in meta_list if isinstance(m, dict) and m.get("doc_id")}

    docs: List[Dict[str, Any]] = []
    for p in updir.glob("*.pdf"):
        did = p.stem
        m = meta_map.get(did, {})
        try:
            ts = datetime.fromtimestamp(p.stat().st_mtime).isoformat()
        except Exception:
            ts = None
        docs.append({
            "doc_id": did,
            "filename": m.get("filename") or p.name,
            "pages": int(m.get("pages") or 0),
            "uploaded_at": ts,
            "title": m.get("title"),
        })

    docs.sort(key=lambda d: d.get("uploaded_at") or "", reverse=True)
    return {"docs": docs}

@app.delete("/documents/{doc_id}")
def delete_doc(doc_id: str, user: User = Depends(get_current_user)):
    INDEX = INDEXES.for_user(user.user_id)
    try:
        INDEX.delete_by_doc(doc_id)
    except Exception:
        pass

    pdf_path = uploads_dir_for(user) / f"{doc_id}.pdf"
    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except Exception:
            pass

    try:
        META = meta_for(user)
        META.delete(doc_id)
    except Exception:
        pass

    return {"ok": True}
