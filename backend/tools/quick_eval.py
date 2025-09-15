# backend/tools/quick_eval.py
import json, sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.embeddings import embed_texts
from retrieval.vector_store import FaissStore

INDEX = FaissStore("./data/index")

def ask(q: str, k=5):
  qemb = embed_texts([q])[0]
  hits = INDEX.search(qemb, k=k)
  for i, h in enumerate(hits, 1):
    print(f"{i}. score={h['score']:.3f}  doc={h['doc_id'][:8]}  page={h['page']}")
    print(h['text'][:180].replace("\n"," ") + "…\n")

if __name__ == "__main__":
  ask("What is this PDF about?", 5)
