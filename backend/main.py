import json
import uuid
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import os, tempfile, sys

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from pydantic_settings import BaseSettings, SettingsConfigDict
from sse_starlette.sse import EventSourceResponse

# auth + per-user index
from auth import get_current_user, User
from services.index_registry import IndexRegistry
from services.storage import LocalStorage

# local imports
from ingestion.pdf_text import extract_pdf_text
from services.embeddings import embed_texts, Settings as EmbSettings
from models.schemas import UploadResponse, AskRequest, AskResult
from models.schemas import ChatRequest, ChatResult
from services.rag import ask_llm, build_messages, stream_openai, citations_from
from services.rerank import mmr_rerank
from services.quality import dedupe_hits, cap_per_doc
from services.telemetry import log_event
from middleware.ratelimit import limit_uploads, limit_chat

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

# test isolation: ensure empty index during pytest
if ("pytest" in sys.modules) or os.getenv("PYTEST_CURRENT_TEST"):
    test_index_dir = Path(tempfile.gettempdir()) / "rag_test_index"
    shutil.rmtree(test_index_dir, ignore_errors=True)
    settings.index_dir = str(test_index_dir)

# per-user registries
INDEXES = IndexRegistry(settings.index_dir)
STORAGE = LocalStorage(settings.upload_dir)

# ─────────────────── FastAPI app ───────────────────
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

# serve raw files (still under /files/{user_id}/{doc_id}.pdf if you link them)
app.mount("/files", StaticFiles(directory=settings.upload_dir), name="files")

# ─────────────────── Helpers ───────────────────
def _filter_hits_by_doc(
    hits: list[Dict[str, Any]], doc_id: str | None, top_k: int
) -> list[Dict[str, Any]]:
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

# ─────────────────── Routes ───────────────────
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/hello")
def hello():
    return {"message": "Backend is running!"}

# ───────────── Upload ─────────────
@app.post("/upload", response_model=UploadResponse, dependencies=[Depends(limit_uploads)])
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # size guard (best-effort)
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > settings.max_pdf_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF too large")

    doc_id = str(uuid.uuid4())
    dest = STORAGE.pdf_path(user.user_id, doc_id)
    dest.parent.mkdir(parents=True, exist_ok=True)

    log.info(f"[UPLOAD] {user.user_id}: {file.filename} -> {dest}")
    try:
        try:
            file.file.seek(0)
        except Exception:
            pass
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except Exception:
        log.exception("[UPLOAD] failed while writing file")
        raise HTTPException(status_code=500, detail="Failed to save file")

    # provisional metadata
    STORAGE.upsert_doc(user.user_id, {
        "doc_id": doc_id,
        "filename": file.filename,
        "pages": 0,
        "uploaded_at": datetime.utcnow().isoformat(),
        "title": None,
    })

    # append to a best-effort queue log
    STORAGE.append_queue(user.user_id, {"doc_id": doc_id, "event": "queued", "ts": datetime.utcnow().isoformat()})

    def _index_pdf():
        try:
            log.info(f"[INDEX] begin: user={user.user_id} doc={doc_id}")
            pages = extract_pdf_text(str(dest))

            # title + chunking
            from ingestion.pdf_text import guess_title
            from ingestion.chunker import smart_chunk_pages
            title = guess_title(pages) or file.filename.rsplit(".", 1)[0]

            # update real page count
            rows = STORAGE.read_meta(user.user_id)
            for r in rows:
                if r.get("doc_id") == doc_id:
                    r["pages"] = len(pages)
                    r["title"] = title
            STORAGE.write_meta(user.user_id, rows)

            chunks = list(smart_chunk_pages(pages, target_chars=900, overlap_chars=120))
            if not chunks:
                log.warning(f"[INDEX] no chunks user={user.user_id} doc={doc_id}")
                return

            texts = [c["text"] for c in chunks]
            embs = embed_texts(texts, model=emb_settings.embed_model)
            metas = [
                {"text": c["text"][:1000], "page": c["page"], "doc_id": doc_id, "title": title}
                for c in chunks
            ]
            index = INDEXES.for_user(user.user_id)
            index.upsert(embs, metas)

            STORAGE.append_queue(user.user_id, {"doc_id": doc_id, "event": "indexed", "ts": datetime.utcnow().isoformat()})
            log.info(f"[INDEX] done: user={user.user_id} doc={doc_id} chunks={len(chunks)}")
        except Exception:
            STORAGE.append_queue(user.user_id, {"doc_id": doc_id, "event": "error", "ts": datetime.utcnow().isoformat()})
            log.exception(f"[INDEX] error user={user.user_id} doc={doc_id}")

    background_tasks.add_task(_index_pdf)
    return {"doc_id": doc_id, "chunks": 0}

# ───────────── Ask (retrieve only) ─────────────
@app.post("/ask", response_model=AskResult)
async def ask(payload: AskRequest, user: User = Depends(get_current_user)):
    index = INDEXES.for_user(user.user_id)
    if getattr(index, "is_empty", None) and index.is_empty():
        return {"results": []}

    doc_id = getattr(payload, "doc_id", None)
    if doc_id and getattr(index, "count", None) and index.count(doc_id) == 0:
        return {"results": []}

    qemb = embed_texts([payload.question])[0]
    hits = index.search(qemb, k=max(50, payload.top_k * 3))
    hits = _filter_hits_by_doc(hits, doc_id, 50)

    hits = dedupe_hits(hits)
    max_per_doc = int(os.getenv("MAX_CHUNKS_PER_DOC", "3"))
    hits = cap_per_doc(hits, per_doc=max_per_doc)
    hits = mmr_rerank(payload.question, hits, top_k=payload.top_k)

    try:
        log_event("ask", {"user": user.user_id, "q": payload.question, "scope": doc_id or "ALL", "n": len(hits)})
    except Exception:
        pass

    for h in hits:
        h["text"] = (h.get("text") or "")[:400]
    return {"results": hits}

# ───────────── Chat (non-streaming) ─────────────
@app.post("/chat")
async def chat(payload: ChatRequest, user: User = Depends(get_current_user), _rl=Depends(limit_chat)):
    index = INDEXES.for_user(user.user_id)
    if getattr(index, "is_empty", None) and index.is_empty():
        return {"answer": "Please upload a PDF first. I don't have any documents to search yet.", "citations": []}

    doc_id = getattr(payload, "doc_id", None)
    if doc_id and getattr(index, "count", None) and index.count(doc_id) == 0:
        return {"answer": "Still indexing that PDF. Try again in a few seconds.", "citations": []}

    qemb = embed_texts([payload.question])[0]
    hits = index.search(qemb, k=max(50, payload.top_k * 3))
    hits = _filter_hits_by_doc(hits, doc_id, 50)
    hits = dedupe_hits(hits)
    hits = cap_per_doc(hits, per_doc=int(os.getenv("MAX_CHUNKS_PER_DOC", "3")))
    hits = mmr_rerank(payload.question, hits, top_k=payload.top_k)

    if not hits or hits[0].get("score", 0) < 0.05:
        return {"answer": "I don't know. I couldn't find enough supporting context.", "citations": []}

    try:
        log_event("chat", {"user": user.user_id, "q": payload.question, "scope": doc_id or "ALL", "n": len(hits)})
    except Exception:
        pass
    return ask_llm(payload.question, hits)

# ───────────── Chat (streaming SSE) ─────────────
@app.get("/chat_stream")
async def chat_stream(
    request: Request,
    question: str,
    top_k: int = 5,
    doc_id: str | None = None,
    user: User = Depends(get_current_user),
    _rl: Any = Depends(limit_chat),
):
    index = INDEXES.for_user(user.user_id)
    if getattr(index, "is_empty", None) and index.is_empty():
        async def no_docs():
            yield {"event": "token", "data": "Please upload a PDF first. I don't have any documents to search yet."}
            yield {"event": "done", "data": '{"citations": []}'}
        return EventSourceResponse(no_docs())

    if doc_id and getattr(index, "count", None) and index.count(doc_id) == 0:
        async def indexing_stream():
            yield {"event": "token", "data": "Still indexing that PDF. "}
            yield {"event": "token", "data": "Try again in a few seconds."}
            yield {"event": "done", "data": '{"citations": []}'}
        return EventSourceResponse(indexing_stream())

    qemb = embed_texts([question])[0]
    hits = index.search(qemb, k=max(50, top_k * 3))
    hits = _filter_hits_by_doc(hits, doc_id, 50)
    hits = dedupe_hits(hits)
    hits = cap_per_doc(hits, per_doc=int(os.getenv("MAX_CHUNKS_PER_DOC", "3")))
    hits = mmr_rerank(question, hits, top_k=top_k)

    try:
        log_event("chat_stream", {"user": user.user_id, "q": question, "scope": doc_id or "ALL", "n": len(hits)})
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
    rows = STORAGE.read_meta(user.user_id)
    # sort newest first (by uploaded_at if present)
    def key(d): return d.get("uploaded_at") or ""
    rows.sort(key=key, reverse=True)
    return {"docs": rows}

@app.delete("/documents/{doc_id}")
def delete_doc(doc_id: str, user: User = Depends(get_current_user)):
    # delete from index
    index = INDEXES.for_user(user.user_id)
    try:
        index.delete_by_doc(doc_id)
    except Exception:
        pass

    # delete pdf
    pdf_path = STORAGE.pdf_path(user.user_id, doc_id)
    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except Exception:
            pass

    STORAGE.delete_doc_meta(user.user_id, doc_id)
    return {"ok": True}
