from typing import List, Dict
from openai import OpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict

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

# ---- Utilities shared by both non-streaming and streaming ----
def _context_from_chunks(chunks: List[Dict], limit: int) -> str:
    parts = []
    for i, c in enumerate(chunks[:limit], 1):
        parts.append(
            f"[CHUNK {i}] (doc_id={c.get('doc_id')}, page={c.get('page')})\n{c.get('text','')}"
        )
    return "\n\n".join(parts)

def build_messages(question: str, retrieved: List[Dict]) -> list[dict]:
    context = _context_from_chunks(retrieved, _settings.max_context_chunks)
    user_msg = f"Question: {question}\n\nContext:\n{context}\n\nAnswer:"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

def citations_from(retrieved: List[Dict]) -> List[Dict]:
    return [
        {"doc_id": c["doc_id"], "page": c["page"], "excerpt": (c.get("text") or "")[:240]}
        for c in retrieved[:_settings.max_context_chunks]
    ]

# ---- Non-streaming RAG (used by /chat) ----
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
