# backend/services/quality.py
from __future__ import annotations
from typing import List, Dict

def _norm(s: str) -> str:
    return " ".join((s or "").split()).lower()

def dedupe_hits(hits: List[Dict]) -> List[Dict]:
    """
    Drop near-duplicates by doc_id+page+first ~200 normalized chars.
    Fast, deterministic, no extra embedding calls.
    """
    seen = set()
    out: List[Dict] = []
    for h in hits:
        key = (h.get("doc_id"), h.get("page"), _norm(h.get("text", ""))[:200])
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out

def cap_per_doc(hits: List[Dict], per_doc: int = 3) -> List[Dict]:
    """
    Keep at most `per_doc` chunks from each document in rank order.
    """
    counts = {}
    out: List[Dict] = []
    for h in hits:
        d = h.get("doc_id")
        c = counts.get(d, 0)
        if c >= per_doc:
            continue
        out.append(h)
        counts[d] = c + 1
    return out
