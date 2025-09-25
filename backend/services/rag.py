from typing import List, Dict
from openai import OpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict
import time

# ---- Settings ----
class Settings(BaseSettings):
    openai_api_key: str
    chat_model: str = "gpt-4o-mini"
    max_context_chunks: int = 3
    # allow extra env vars (e.g., EMBED_MODEL, INDEX_DIR, etc.)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

_settings = Settings()
_client = OpenAI(api_key=_settings.openai_api_key)

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers ONLY using the provided context. "
    "If the answer is not in the context, say you don't know. "
    "Cite sources as (doc_id:page). Keep answers concise."
)
def _retry(n=2, wait=1.0):
    def deco(fn):
        def wrap(*a, **k):
            last = None
            for i in range(n+1):
                try:
                    return fn(*a, **k)
                except Exception as e:
                    last = e
                    if i < n:
                        time.sleep(wait)
            raise last
        return wrap
    return deco
# ---- Utilities shared by both non-streaming and streaming ----
def _context_from_chunks(chunks: List[Dict], limit: int) -> str:
    parts = []
    for i, c in enumerate(chunks[:limit], 1):
        parts.append(
            f"[CHUNK {i}] (doc_id={c.get('doc_id')}, page={c.get('page')})\n{c.get('text','')}"
        )
    return "\n\n".join(parts)

def build_messages(question: str, hits: list[dict]) -> list[dict]:
    """
    Include minimal, relevant chunks with citations. Encourage grounded answers.
    """
    context_blocks = []
    for h in hits:
        title = h.get("title") or ""
        page = h.get("page")
        txt = h.get("text", "")
        tag = f"{h.get('doc_id','')}:p{page}"
        header = f"[{title}] ({tag})" if title else f"({tag})"
        context_blocks.append(f"{header}\n{txt}")

    context = "\n\n".join(context_blocks)

    system = (
        "You are an assistant that answers ONLY using the provided context.\n"
        "• Cite sources inline as (doc_id:page) right after the sentence.\n"
        "• If the answer is not in context, reply: “I don’t know based on the provided documents.”\n"
        "• Be concise and specific."
    )
    user = f"Question: {question}\n\nContext:\n{context}\n\nAnswer:"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

def citations_from(retrieved: List[Dict]) -> List[Dict]:
    return [
        {"doc_id": c["doc_id"], "page": c["page"], "excerpt": (c.get("text") or "")[:240]}
        for c in retrieved[:_settings.max_context_chunks]
    ]

# ---- Non-streaming RAG (used by /chat) ----
@_retry(n=2, wait=1.0)
def ask_llm(question: str, retrieved: List[Dict]) -> Dict:
    messages = build_messages(question, retrieved)
    resp = _client.chat.completions.create(
        model=_settings.chat_model,
        messages=messages,
        temperature=0.2,
    )
    answer = resp.choices[0].message.content.strip()
    return {"answer": answer, "citations": citations_from(retrieved)}

# ---- Streaming RAG (used by /chat_stream) ----
@_retry(n=2, wait=1.0)
def stream_openai(messages: list[dict]):
    """Yield token deltas from OpenAI stream=True API."""
    stream = _client.chat.completions.create(
        model=_settings.chat_model,
        messages=messages,
        temperature=0.2,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta
