# backend/eval/run_eval.py
from __future__ import annotations
import json, os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import statistics as stats

# Reuse your app retrieval functions via HTTP for realism—or import the store+embed stack directly.
# To keep this setup-free, we import the retrieval pipeline from the app modules:
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))  # add backend/ to path

from services.embeddings import embed_texts, Settings as EmbSettings
from retrieval.vector_store import FaissStore
from services.rerank import mmr_rerank
from services.quality import dedupe_hits, cap_per_doc

# Config
DATA_PATH = Path("./eval/devset.jsonl")
INDEX_DIR = os.getenv("INDEX_DIR", "./data/index")
TOP_K = int(os.getenv("EVAL_TOP_K", "5"))
PER_DOC = int(os.getenv("EVAL_PER_DOC", "3"))

def load_devset() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}. Add JSONL items as described in its header.")
    return [json.loads(line) for line in DATA_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]

def retrieval_only(question: str, index: FaissStore, top_k: int) -> List[Dict]:
    qemb = embed_texts([question])[0]
    hits = index.search(qemb, k=max(50, top_k*3))
    hits = dedupe_hits(hits)
    hits = cap_per_doc(hits, per_doc=PER_DOC)
    hits = mmr_rerank(question, hits, top_k=top_k)
    return hits[:top_k]

def recall_at_k(hits: List[Dict], gold_doc_id: str | None, gold_page: int | None) -> float:
    if gold_doc_id is None:
        return float('nan')  # unknown; exclude from strict recall
    for h in hits:
        if h.get("doc_id") == gold_doc_id and (gold_page is None or h.get("page") == gold_page):
            return 1.0
    return 0.0

def mrr_at_k(hits: List[Dict], gold_doc_id: str | None, gold_page: int | None) -> float:
    if gold_doc_id is None:
        return float('nan')
    for i, h in enumerate(hits, 1):
        if h.get("doc_id") == gold_doc_id and (gold_page is None or h.get("page") == gold_page):
            return 1.0 / i
    return 0.0

def string_contains(pred: str, gold: str) -> bool:
    return gold.lower() in pred.lower()

def main():
    index = FaissStore(INDEX_DIR)
    devset = load_devset()

    rows = []
    recs, mrrs, contains = [], [], []
    for ex in devset:
        q = ex["question"]
        hits = retrieval_only(q, index, TOP_K)
        # run your answerer if you want end-to-end accuracy:
        # from services.rag import ask_llm, build_messages
        # ans = ask_llm(q, hits)["answer"]

        # cheap heuristic: copy most relevant snippet as pseudo-answer
        ans = (hits[0].get("text", "") if hits else "").strip()

        r = recall_at_k(hits, ex.get("gold_doc_id"), ex.get("gold_page"))
        m = mrr_at_k(hits, ex.get("gold_doc_id"), ex.get("gold_page"))
        c = string_contains(ans, ex.get("gold_answer","")) if ex.get("gold_answer") else float('nan')

        rows.append({"id": ex["id"], "recall@k": r, "mrr@k": m, "contains": c})
        if not (r != r): recs.append(r)   # skip NaN
        if not (m != m): mrrs.append(m)
        if not (c != c): contains.append(c)

    out_dir = Path("./eval/out"); out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "k": TOP_K,
        "per_doc_cap": PER_DOC,
        "n_items": len(devset),
        "retrieval": {
            "recall@k_mean": stats.mean(recs) if recs else None,
            "mrr@k_mean": stats.mean(mrrs) if mrrs else None,
        },
        "answer": {
            "contains_mean": stats.mean(contains) if contains else None
        },
        "rows": rows,
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
