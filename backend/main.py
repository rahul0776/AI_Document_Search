# backend/main.py
from __future__ import annotations

import json
import uuid
import shutil
import logging
import time
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
from auth import get_current_user, get_current_user_query, User, issue_token
from services.user_store import get_user_store
from services.email_service import get_email_service
from services.token_service import get_token_service

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

# ── Advanced RAG features (Day 5-7)
from retrieval.hybrid_search import get_hybrid_searcher
from retrieval.query_expansion import expand_query_simple
from retrieval.advanced_rerank import get_reranker
from services.context_optimizer import get_context_optimizer
from services.rag_evaluator import get_evaluator
from ingestion.smart_chunker import chunk_documents_smart

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
    top_k_default: int = 10
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
emb_settings = EmbSettings()

# Create required directories on startup
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.index_dir, exist_ok=True)
os.makedirs("./data/logs", exist_ok=True)

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
        "https://ai-document-search.vercel.app",  # Production frontend
        "http://localhost:5173",
        "http://localhost:3000",
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

# ─────────────────── Auth ───────────────────
@app.post("/auth/signup")
def signup(body: Dict[str, Any]):
    """
    Create a new user account with email verification.
    POST {"username": "...", "email": "...", "password": "..."}
    """
    if body is None:
        raise HTTPException(status_code=400, detail="JSON body required")
    
    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    
    # Validation
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    user_store = get_user_store()
    
    if user_store.user_exists(username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already used
    existing_user = user_store.get_user_by_email(email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate email verification token
    token_service = get_token_service()
    verification_token, token_hash, expiry = token_service.create_verification_token()
    
    # Create user with verification token
    success = user_store.create_user(
        username, 
        password, 
        email,
        verification_token_hash=token_hash,
        verification_token_expiry=expiry
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    # Send verification email
    email_service = get_email_service()
    email_sent = email_service.send_verification_email(email, username, verification_token)
    
    # Issue JWT token (user can use app but should verify email)
    token = issue_token(user_id=username, email=email, hours=24)
    
    return {
        "token": token, 
        "user": {"user_id": username, "email": email, "email_verified": False},
        "message": "Account created! Please check your email to verify your account." if email_sent else "Account created!"
    }

@app.post("/auth/login")
def login(body: Dict[str, Any]):
    """
    Login with username and password.
    POST {"username": "...", "password": "..."}
    """
    if body is None:
        raise HTTPException(status_code=400, detail="JSON body required")
    
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    
    user_store = get_user_store()
    user = user_store.verify_user(username, password)
    
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = issue_token(user_id=username, email=user.get("email"), hours=24)
    return {"token": token, "user": {"user_id": username, "email": user.get("email")}}

@app.post("/auth/dev_login")
def dev_login(body: Dict[str, Any]):
    """
    Dev-only endpoint to mint a JWT for quick testing (bypasses password).
    POST {"user_id": "demo", "email": "demo@example.com"}
    Only use in development!
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
    user_store = get_user_store()
    user_data = user_store.get_user(user.user_id)
    return {
        "user_id": user.user_id, 
        "email": user.email,
        "email_verified": user_data.get("email_verified", False) if user_data else False
    }

# ─────────────────── Email Verification ───────────────────
@app.post("/auth/verify-email")
def verify_email(body: Dict[str, Any]):
    """
    Verify user's email with token from email link.
    POST {"token": "..."}
    """
    if body is None:
        raise HTTPException(status_code=400, detail="JSON body required")
    
    token = body.get("token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Verification token is required")
    
    token_service = get_token_service()
    user_store = get_user_store()
    
    # Hash the token to find the user
    token_hash = token_service.hash_token(token)
    username = user_store.find_user_by_verification_token(token_hash)
    
    if not username:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    # Get token data
    token_data = user_store.get_verification_token(username)
    if not token_data or not token_data.get("token_hash"):
        raise HTTPException(status_code=400, detail="No verification token found")
    
    # Verify token
    is_valid = token_service.verify_token(
        token, 
        token_data["token_hash"], 
        token_data["expiry"]
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    # Mark email as verified
    success = user_store.verify_email(username)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to verify email")
    
    # Send welcome email
    user_data = user_store.get_user(username)
    if user_data and user_data.get("email"):
        email_service = get_email_service()
        email_service.send_welcome_email(user_data["email"], username)
    
    return {
        "ok": True,
        "message": "Email verified successfully! Welcome to AI Document Search."
    }

@app.post("/auth/resend-verification")
def resend_verification(user: User = Depends(get_current_user)):
    """
    Resend verification email to current user.
    Requires authentication.
    """
    user_store = get_user_store()
    user_data = user_store.get_user(user.user_id)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_data.get("email_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")
    
    if not user_data.get("email"):
        raise HTTPException(status_code=400, detail="No email associated with account")
    
    # Generate new verification token
    token_service = get_token_service()
    verification_token, token_hash, expiry = token_service.create_verification_token()
    
    # Update user with new token
    users = user_store._load_users()
    users[user.user_id]["verification_token_hash"] = token_hash
    users[user.user_id]["verification_token_expiry"] = expiry
    user_store._save_users(users)
    
    # Send email
    email_service = get_email_service()
    email_sent = email_service.send_verification_email(
        user_data["email"], 
        user.user_id, 
        verification_token
    )
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send verification email")
    
    return {
        "ok": True,
        "message": "Verification email sent! Please check your inbox."
    }

# ─────────────────── Password Reset ───────────────────
@app.post("/auth/forgot-password")
def forgot_password(body: Dict[str, Any]):
    """
    Request password reset email.
    POST {"email": "..."}
    """
    if body is None:
        raise HTTPException(status_code=400, detail="JSON body required")
    
    email = (body.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user_store = get_user_store()
    username = user_store.get_user_by_email(email)
    
    # Always return success (don't reveal if email exists)
    if not username:
        return {
            "ok": True,
            "message": "If that email is registered, you will receive a password reset link shortly."
        }
    
    # Generate reset token
    token_service = get_token_service()
    reset_token, token_hash, expiry = token_service.create_password_reset_token()
    
    # Store reset token
    success = user_store.set_password_reset_token(username, token_hash, expiry)
    if not success:
        log.error(f"Failed to set password reset token for {username}")
        return {
            "ok": True,
            "message": "If that email is registered, you will receive a password reset link shortly."
        }
    
    # Send reset email
    email_service = get_email_service()
    email_sent = email_service.send_password_reset_email(email, username, reset_token)
    
    if not email_sent:
        log.error(f"Failed to send password reset email to {email}")
    
    return {
        "ok": True,
        "message": "If that email is registered, you will receive a password reset link shortly."
    }

@app.post("/auth/reset-password")
def reset_password(body: Dict[str, Any]):
    """
    Reset password with token from email.
    POST {"token": "...", "new_password": "..."}
    """
    if body is None:
        raise HTTPException(status_code=400, detail="JSON body required")
    
    token = body.get("token", "").strip()
    new_password = body.get("new_password", "")
    
    if not token:
        raise HTTPException(status_code=400, detail="Reset token is required")
    if not new_password:
        raise HTTPException(status_code=400, detail="New password is required")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    token_service = get_token_service()
    user_store = get_user_store()
    
    # Hash the token to find the user
    token_hash = token_service.hash_token(token)
    username = user_store.find_user_by_reset_token(token_hash)
    
    if not username:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Get token data
    token_data = user_store.get_password_reset_token(username)
    if not token_data or not token_data.get("token_hash"):
        raise HTTPException(status_code=400, detail="No reset token found")
    
    # Verify token
    is_valid = token_service.verify_token(
        token, 
        token_data["token_hash"], 
        token_data["expiry"]
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Reset password
    success = user_store.reset_password(username, new_password)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset password")
    
    return {
        "ok": True,
        "message": "Password reset successfully! You can now log in with your new password."
    }

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
    hits = cap_per_doc(hits, per_doc=int(os.getenv("MAX_CHUNKS_PER_DOC", "5")))
    hits = mmr_rerank(payload.question, hits, top_k=payload.top_k)

    try:
        log_event("ask", {"user_id": user.user_id, "q": payload.question, "scope": doc_id or "ALL", "n": len(hits)})
    except Exception:
        pass

    for h in hits:
        h["text"] = (h.get("text") or "")[:400]
    return {"results": hits}

# ───────────── Advanced RAG Helper ─────────────
def advanced_rag_retrieve(
    question: str,
    INDEX,
    doc_id: Optional[str] = None,
    top_k: int = 10,
    use_advanced: bool = True
) -> List[Dict]:
    """
    Advanced RAG retrieval pipeline with all improvements.
    
    Pipeline:
    1. Query expansion
    2. Semantic search (FAISS)
    3. Hybrid search (BM25 + semantic)
    4. Cross-encoder reranking
    5. Context optimization
    """
    start_time = time.time()
    
    # Step 1: Query expansion for better retrieval
    if use_advanced and os.getenv("ENABLE_QUERY_EXPANSION", "1") == "1":
        expanded_question = expand_query_simple(question)
        log.info(f"Query expanded: '{question}' → '{expanded_question}'")
    else:
        expanded_question = question
    
    # Step 2: Semantic search with expanded query
    qemb = embed_texts([expanded_question])[0]
    semantic_hits = INDEX.search(qemb, k=max(50, top_k * 5))  # Get more for better reranking
    semantic_hits = _filter_hits_by_doc(semantic_hits, doc_id, 100)
    semantic_hits = dedupe_hits(semantic_hits)
    
    # Step 3: Hybrid search (combine semantic + BM25)
    if use_advanced and os.getenv("ENABLE_HYBRID_SEARCH", "1") == "1":
        try:
            hybrid_searcher = get_hybrid_searcher(alpha=0.7)  # 70% semantic, 30% BM25
            
            # Index corpus for BM25 (if not already done)
            if not hybrid_searcher.corpus_texts or len(hybrid_searcher.corpus_texts) != len(semantic_hits):
                texts = [hit.get("text", "") for hit in semantic_hits]
                hybrid_searcher.index_corpus(texts, semantic_hits)
            
            # Perform hybrid search
            hits = hybrid_searcher.search(question, semantic_hits, top_k=top_k * 3)
            log.info(f"Hybrid search: {len(semantic_hits)} → {len(hits)} results")
        except Exception as e:
            log.error(f"Hybrid search failed: {e}, using semantic only")
            hits = semantic_hits
    else:
        hits = semantic_hits
    
    # Step 4: Cap per document and dedupe
    hits = cap_per_doc(hits, per_doc=int(os.getenv("MAX_CHUNKS_PER_DOC", "5")))
    
    # Step 5: Cross-encoder reranking for accuracy
    if use_advanced and os.getenv("ENABLE_RERANKING", "1") == "1":
        try:
            reranker = get_reranker()
            hits = reranker.rerank(question, hits, top_k=top_k * 2)
            log.info(f"Reranked results with cross-encoder")
        except Exception as e:
            log.error(f"Reranking failed: {e}, using original order")
    
    # Step 6: Context optimization
    if use_advanced:
        try:
            optimizer = get_context_optimizer()
            hits = optimizer.optimize_context(hits, max_chunks=top_k)
            log.info(f"Context optimized: {len(hits)} final chunks")
        except Exception as e:
            log.error(f"Context optimization failed: {e}")
            hits = hits[:top_k]
    else:
        hits = mmr_rerank(question, hits, top_k=top_k)
    
    # Log metrics
    retrieval_time = time.time() - start_time
    try:
        evaluator = get_evaluator()
        avg_score = sum(h.get("hybrid_score", h.get("score", 0)) for h in hits) / len(hits) if hits else 0
        evaluator.log_retrieval(
            query=question,
            results_count=len(hits),
            avg_score=avg_score,
            retrieval_time=retrieval_time,
            method="advanced_rag" if use_advanced else "standard"
        )
    except Exception:
        pass
    
    return hits


# ───────────── Chat (non-streaming) ─────────────
@app.post("/chat", dependencies=[Depends(limit_chat)])
async def chat(payload: ChatRequest, user: User = Depends(get_current_user)):
    INDEX = INDEXES.for_user(user.user_id)

    if hasattr(INDEX, "is_empty") and INDEX.is_empty():
        return {"answer": "Please upload a PDF first. I don't have any documents to search yet.", "citations": []}

    doc_id = getattr(payload, "doc_id", None)
    if doc_id and hasattr(INDEX, "count") and INDEX.count(doc_id) == 0:
        return {"answer": "Still indexing that PDF. Try again in a few seconds.", "citations": []}

    # Use advanced RAG pipeline
    use_advanced = os.getenv("ENABLE_ADVANCED_RAG", "1") == "1"
    hits = advanced_rag_retrieve(payload.question, INDEX, doc_id, payload.top_k, use_advanced)

    if not hits or hits[0].get("score", 0) < 0.05:
        return {"answer": "I don't know. I couldn't find enough supporting context.", "citations": []}

    try:
        log_event("chat", {"user_id": user.user_id, "q": payload.question, "scope": doc_id or "ALL", "n": len(hits), "advanced": use_advanced})
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
    token: Optional[str] = None,  # Accept token as query param for EventSource
):
    # Auth: EventSource can't set headers, so we accept token as query param
    user = get_current_user_query(token)
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

    # Use advanced RAG pipeline
    use_advanced = os.getenv("ENABLE_ADVANCED_RAG", "1") == "1"
    hits = advanced_rag_retrieve(question, INDEX, doc_id, top_k, use_advanced)

    try:
        log_event("chat_stream", {"user_id": user.user_id, "q": question, "scope": doc_id or "ALL", "n": len(hits), "advanced": use_advanced})
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
        import asyncio
        last_ping = time.time()
        for piece in stream_openai(messages):
            if await request.is_disconnected():
                break
            yield {"event": "token", "data": piece}
            # Send periodic heartbeat to keep connection alive
            if time.time() - last_ping > 15:
                yield {"event": "ping", "data": ""}
                last_ping = time.time()
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

# For Railway deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
