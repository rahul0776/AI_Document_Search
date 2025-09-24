# backend/services/rerank.py
from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
from services.embeddings import embed_texts

def _cos(a: np.ndarray, b: np.ndarray) -> float:
    da = np.linalg.norm(a) + 1e-9
    db = np.linalg.norm(b) + 1e-9
    return float(np.dot(a, b) / (da * db))

def mmr_rerank(
    question: str,
    hits: List[Dict[str, Any]],
    top_k: int = 5,
    lambda_mult: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Re-embed texts of top hits and select MMR subset.
    """
    if not hits:
        return hits
    K = min(len(hits), max(10, top_k * 3))  # re-rank a bit wider
    cand = hits[:K]
    qvec = embed_texts([question])[0]
    dvecs = embed_texts([c.get("text","") for c in cand])

    selected: List[int] = []
    remaining = list(range(len(cand)))

    while remaining and len(selected) < top_k:
        if not selected:
            # pick most similar to query
            idx = max(remaining, key=lambda i: _cos(qvec, dvecs[i]))
            selected.append(idx)
            remaining.remove(idx)
            continue

        # MMR: choose doc with highest lambda*sim(q,di) - (1-lambda)*max_j sim(di, dj_selected)
        best_i = None
        best_score = -1e9
        for i in remaining:
            sim_q = _cos(qvec, dvecs[i])
            sim_div = max(_cos(dvecs[i], dvecs[j]) for j in selected)
            score = lambda_mult * sim_q - (1 - lambda_mult) * sim_div
            if score > best_score:
                best_score = score
                best_i = i
        selected.append(best_i)
        remaining.remove(best_i)

    # decorate with rerank score (similarity to query)
    out = [cand[i].copy() for i in selected]
    for o, i in zip(out, selected):
        o["rerank"] = _cos(qvec, dvecs[i])
    return out
