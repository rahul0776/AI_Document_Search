import json
import uuid
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from pydantic_settings import BaseSettings, SettingsConfigDict
from sse_starlette.sse import EventSourceResponse

# local imports
from ingestion.pdf_text import extract_pdf_text
from ingestion.chunker import chunk_pages
from services.embeddings import embed_texts, Settings as EmbSettings
from retrieval.vector_store import FaissStore
from models.schemas import UploadResponse, AskRequest, AskResult
from models.schemas import ChatRequest, ChatResult
from services.rag import ask_llm, build_messages, stream_openai, citations_from
from services.docmeta import DocMetaStore

log = logging.getLogger("uvicorn.error")

# ─────────────────── Settings ───────────────────
class Settings(BaseSettings):
    frontend_origin: str = "http://localhost:3000"
    index_dir: str = "./data/index"
    upload_dir: str = "./data/uploads"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
emb_settings = EmbSettings()
META = DocMetaStore(settings.upload_dir)

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

INDEX = FaissStore(settings.index_dir)
app.mount("/files", StaticFiles(directory=settings.upload_dir), name="files")


# ─────────────────── Helpers ───────────────────
def _filter_hits_by_doc(
    hits: list[Dict[str, Any]], doc_id: str | None, top_k: int
) -> list[Dict[str, Any]]:
    """
    Retrieve wider (already done by caller), optionally filter by doc_id, and trim to top_k.
    """
    if doc_id:
        hits = [h for h in hits if h.get("doc_id") == doc_id]
    return hits[:top_k]


# ─────────────────── Routes ───────────────────
@app.get("/health")
def health():
    return {"ok": True}


@app.get("/hello")
def hello():
    return {"message": "Backend is running!"}


@app.post("/upload", response_model=UploadResponse)
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # 0) quick sanity
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # 1) stream to disk (no await file.read())
    doc_id = str(uuid.uuid4())
    updir = Path(settings.upload_dir)
    updir.mkdir(parents=True, exist_ok=True)
    dest = updir / f"{doc_id}.pdf"

    log.info(f"[UPLOAD] start: {file.filename} -> {dest}")
    try:
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)  # stream to disk
    except Exception:
        log.exception("Failed to save uploaded file")
        raise HTTPException(status_code=500, detail="Failed to save file")

    # 1.5) write provisional metadata immediately so it appears in /docs
    try:
        META.add(doc_id, file.filename, pages=0)
    except Exception:
        log.exception(f"[META] provisional add failed for {doc_id}")

    # 2) index asynchronously (do NOT do heavy work inline)
    def _index_pdf():
        try:
            log.info(f"[INDEX] begin: {doc_id}")
            pages = extract_pdf_text(str(dest))
            chunks = list(chunk_pages(pages, chunk_chars=1200, overlap=150))

            # update real page count in metadata
            try:
                META.add(doc_id, file.filename, pages=len(pages))
            except Exception:
                pass

            if not chunks:
                log.warning(f"[INDEX] no chunks for {doc_id}")
                return 0

            texts = [c["text"] for c in chunks]
            embs = embed_texts(texts, model=emb_settings.embed_model)
            metas = [{"text": c["text"][:1000], "page": c["page"], "doc_id": doc_id} for c in chunks]
            INDEX.upsert(embs, metas)
            log.info(f"[INDEX] done: {doc_id} chunks={len(chunks)}")
            return len(chunks)
        except Exception:
            log.exception(f"[INDEX] error for doc_id={doc_id}")
            return 0

    background_tasks.add_task(_index_pdf)

    # 3) return immediately
    log.info(f"[UPLOAD] ok: {doc_id}")
    return {"doc_id": doc_id, "chunks": 0}


# ───────────── Ask (retrieve only) ─────────────
@app.post("/ask", response_model=AskResult)
async def ask(payload: AskRequest):
    """
    Accepts optional payload.doc_id to limit hits to a single PDF.
    """
    qemb = embed_texts([payload.question])[0]
    # retrieve wider, then filter & trim
    hits = INDEX.search(qemb, k=max(50, payload.top_k))

    doc_id = getattr(payload, "doc_id", None)  # optional if your schema lacks it
    hits = _filter_hits_by_doc(hits, doc_id, payload.top_k)

    # Trim text for frontend display
    for h in hits:
        h["text"] = (h.get("text") or "")[:400]

    return {"results": hits}


# ───────────── Chat (non-streaming) ─────────────
@app.post("/chat", response_model=ChatResult)
async def chat(payload: ChatRequest):
    """
    Accepts optional payload.doc_id to limit hits to a single PDF.
    """
    qemb = embed_texts([payload.question])[0]
    hits = INDEX.search(qemb, k=max(50, payload.top_k))

    doc_id = getattr(payload, "doc_id", None)
    hits = _filter_hits_by_doc(hits, doc_id, payload.top_k)

    if not hits or hits[0].get("score", 0) < 0.05:  # simple low-confidence guard
        return {"answer": "I don't know. I couldn't find enough supporting context.", "citations": []}

    return ask_llm(payload.question, hits)


# ───────────── Chat (streaming SSE) ─────────────
@app.get("/chat_stream")
async def chat_stream(
    request: Request,
    question: str,
    top_k: int = 5,
    doc_id: str | None = None,
):
    """
    Server-Sent Events stream:
      - event: 'token'  data: <string token>
      - event: 'done'   data: {"citations":[...]}
    """
    qemb = embed_texts([question])[0]
    hits = INDEX.search(qemb, k=max(50, top_k))
    hits = _filter_hits_by_doc(hits, doc_id, top_k)

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
def list_docs():
    """
    Returns: [{doc_id, filename, pages, uploaded_at}]
    Combines metadata with files found in upload_dir so the list is robust.
    """
    updir = Path(settings.upload_dir)
    updir.mkdir(parents=True, exist_ok=True)

    try:
        meta_list = META.all() or []
    except Exception:
        meta_list = []

    meta_map: Dict[str, Dict[str, Any]] = {}
    for m in meta_list:
        if isinstance(m, dict) and m.get("doc_id"):
            meta_map[m["doc_id"]] = m

    docs: list[Dict[str, Any]] = []
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
        })

    docs.sort(key=lambda d: d.get("uploaded_at") or "", reverse=True)
    return {"docs": docs}


@app.delete("/documents/{doc_id}")
def delete_doc(doc_id: str):
    try:
        INDEX.delete_by_doc(doc_id)
    except Exception:
        pass

    pdf_path = Path(settings.upload_dir) / f"{doc_id}.pdf"
    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except Exception:
            pass

    try:
        META.delete(doc_id)
    except Exception:
        pass

    return {"ok": True}