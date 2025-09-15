import json
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import uuid
from sse_starlette.sse import EventSourceResponse
from typing import Dict, Any
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
# local imports
from ingestion.pdf_text import extract_pdf_text
from ingestion.chunker import chunk_pages
from services.embeddings import embed_texts, Settings as EmbSettings
from retrieval.vector_store import FaissStore
from models.schemas import UploadResponse, AskRequest, AskResult
from models.schemas import ChatRequest, ChatResult
from services.rag import ask_llm, build_messages, stream_openai, citations_from

# ─────────────────── Settings ───────────────────
class Settings(BaseSettings):
    frontend_origin: str = "http://localhost:3000"
    index_dir: str = "./data/index"
    upload_dir: str = "./data/uploads"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
emb_settings = EmbSettings()

# ─────────────────── FastAPI app ───────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",   # vite dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INDEX = FaissStore(settings.index_dir)
app.mount("/files", StaticFiles(directory=settings.upload_dir), name="files")

# ─────────────────── Routes ───────────────────
@app.get("/health")
def health():
    return {"ok": True}


@app.get("/hello")
def hello():
    return {"message": "Backend is running!"}


@app.post("/upload", response_model=UploadResponse)
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # 1) save file
    if not file.filename.lower().endswith(".pdf") or file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    doc_id = str(uuid.uuid4())
    updir = Path(settings.upload_dir)
    updir.mkdir(parents=True, exist_ok=True)
    dest = updir / f"{doc_id}.pdf"
    with open(dest, "wb") as f:
        f.write(await file.read())

    # 2) index asynchronously
    def _index_pdf():
        pages = extract_pdf_text(str(dest))
        chunks = list(chunk_pages(pages, chunk_chars=1200, overlap=150))
        if not chunks:
            return 0
        texts = [c["text"] for c in chunks]
        embs = embed_texts(texts, model=emb_settings.embed_model)
        metas = [{"text": c["text"][:1000], "page": c["page"], "doc_id": doc_id} for c in chunks]
        INDEX.upsert(embs, metas)
        return len(chunks)

    background_tasks.add_task(_index_pdf)
    return {"doc_id": doc_id, "chunks": 0}
@app.post("/chat", response_model=ChatResult)
async def chat(payload: ChatRequest):
    qemb = embed_texts([payload.question])[0]
    hits = INDEX.search(qemb, k=payload.top_k)

    if not hits or hits[0]["score"] < 0.05:  # simple low-confidence guard
        return {"answer": "I don't know. I couldn't find enough supporting context.",
                "citations": []}

    return ask_llm(payload.question, hits)

@app.post("/ask", response_model=AskResult)
async def ask(payload: AskRequest):
    # Embed the question and search
    qemb = embed_texts([payload.question])[0]
    hits = INDEX.search(qemb, k=payload.top_k)

    # Trim text for frontend
    for h in hits:
        h["text"] = (h.get("text") or "")[:400]

    return {"results": hits}

@app.get("/chat_stream")
async def chat_stream(request: Request, question: str, top_k: int = 5):
    """
    Server-Sent Events stream:
      - event: 'token'  data: <string token>
      - event: 'done'   data: {"citations":[...]}
    Use GET so EventSource works naturally.
    """
    # 1) retrieve
    qemb = embed_texts([question])[0]
    hits = INDEX.search(qemb, k=top_k)

    # if no good context, send a short message and done
    if not hits or hits[0].get("score", 0) < 0.05:
        async def no_context_stream():
            yield {"event": "token", "data": "I don't know. I couldn't find enough supporting context."}
            yield {"event": "done", "data": '{"citations": []}'}
        return EventSourceResponse(no_context_stream())

    messages = build_messages(question, hits)
    cits_json = json.dumps({"citations": citations_from(hits)})

    # 2) stream tokens from OpenAI
    async def event_generator():
        # FastAPI wants an async generator; we wrap the sync OpenAI generator
        for piece in stream_openai(messages):
            # client disconnected?
            if await request.is_disconnected():
                break
            yield {"event": "token", "data": piece}
        # finally send citations
        yield {"event": "done", "data": cits_json}

    return EventSourceResponse(event_generator())