# backend/services/rag.py
from __future__ import annotations

from typing import List, Dict, Iterable
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# ─────────────────── Settings ───────────────────
class Settings(BaseSettings):
    openai_api_key: str
    chat_model: str = "gpt-4o-mini"

    # How many retrieved chunks to expose as citations in the UI
    max_context_chunks: int = 5

    # Hard cap on total context characters sent to the LLM
    max_context_chars: int = 15000

    # Robustness knobs
    openai_timeout_s: int = 45
    openai_retries: int = 3

    # allow extra env vars (EMBED_MODEL, INDEX_DIR, etc.)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


_settings = Settings()

# OpenAI client with request timeout
_client = OpenAI(api_key=_settings.openai_api_key, timeout=_settings.openai_timeout_s)

SYSTEM_PROMPT = (
    "You are an intelligent document assistant. Your role is to provide comprehensive, accurate answers based on the provided context. "
    "Guidelines:\n"
    "- Synthesize information from ALL provided context sections to give complete answers\n"
    "- If multiple parts of the document are relevant, combine them into a coherent response\n"
    "- Be thorough but clear - don't leave out important details that are in the context\n"
    "- If the answer requires information from different sections, connect them logically\n"
    "- Only if the answer is truly not in ANY of the provided context, say: 'I don't have enough information in the provided documents to answer that.'\n"
    "- Use a conversational, helpful tone\n"
    "- Format your response with proper paragraphs for readability\n"
    "- When relevant, include specific details, numbers, or examples from the documents"
)

# ─────────────────── Prompt construction ───────────────────
def build_messages(question: str, hits: List[Dict]) -> List[Dict[str, str]]:
    """
    Build a compact, grounded prompt:
    - Prefix each chunk with a tag including short doc_id and page.
    - Enforce a soft char budget across chunks to avoid overly long prompts.
    """
    parts: List[str] = []
    used = 0
    budget = max(1000, int(_settings.max_context_chars))  # safety lower bound

    for h in hits:
        txt = (h.get("text") or "").strip()
        if not txt:
            continue

        title = h.get("title") or ""
        page = h.get("page")
        doc_id = h.get("doc_id", "")
        tag = f"{doc_id[:8]}:p{page}"
        header = f"[{title}] ({tag})" if title else f"({tag})"

        remaining = budget - used
        if remaining <= 0:
            break
        if len(txt) > remaining:
            txt = txt[:remaining]

        parts.append(f"{header}\n{txt}")
        used += len(txt)

        if used >= budget:
            break

    context = "\n\n---\n\n".join(parts) if parts else "(no context)"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Question:\n{question}\n\nContext:\n{context}\n\nAnswer:",
        },
    ]


def citations_from(retrieved: List[Dict]) -> List[Dict]:
    """
    Take the first N retrieved items and expose minimal citation metadata for the UI.
    """
    out: List[Dict] = []
    for c in retrieved[: max(1, _settings.max_context_chunks)]:
        out.append(
            {
                "doc_id": c.get("doc_id", ""),
                "page": int(c.get("page", 0)),
                "excerpt": (c.get("text") or "")[:240],
            }
        )
    return out


# ─────────────────── OpenAI calls (with retries) ───────────────────
@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(max(1, _settings.openai_retries)),
    retry=retry_if_exception_type((APIConnectionError, RateLimitError, APIStatusError)),
    reraise=True,
)
def _chat(messages: List[Dict[str, str]]) -> str:
    """
    Non-streaming chat completion with retry on transient OpenAI errors.
    """
    resp = _client.chat.completions.create(
        model=_settings.chat_model,
        messages=messages,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


def stream_openai(messages: List[Dict[str, str]]) -> Iterable[str]:
    """
    Streaming generator (no retries mid-stream; caller can decide fallback).
    Yields token deltas as strings.
    """
    stream = _client.chat.completions.create(
        model=_settings.chat_model,
        messages=messages,
        temperature=0.2,
        stream=True,
    )
    for chunk in stream:
        piece = chunk.choices[0].delta.content or ""
        if piece:
            yield piece


# ─────────────────── Public RAG helpers ───────────────────
def ask_llm(question: str, retrieved: List[Dict]) -> Dict:
    """
    Build messages, call OpenAI (with retries), and return the answer + citations.
    """
    messages = build_messages(question, retrieved)
    answer = _chat(messages)
    return {"answer": answer, "citations": citations_from(retrieved)}
