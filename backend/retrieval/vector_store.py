from __future__ import annotations
from pathlib import Path
import json, faiss, numpy as np
from typing import List, Dict

class FaissStore:
    def __init__(self, index_dir: str):
        self.dir = Path(index_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.dir / "meta.jsonl"
        self.index_file = self.dir / "index.faiss"
        self.dim = None
        self.index = None
        self._load()

    def _load(self):
        if self.index_file.exists():
            self.index = faiss.read_index(str(self.index_file))
            # dim inferred
            self.dim = self.index.d
        else:
            self.index = None
        if not self.meta_file.exists():
            self.meta_file.touch()

    def _ensure(self, dim: int):
        if self.index is None:
            self.index = faiss.IndexFlatIP(dim)  # cosine-like (normalize)
            self.dim = dim

    def _append_meta(self, items: List[Dict]):
        with self.meta_file.open("a", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")

    @staticmethod
    def _normalize(vecs: np.ndarray) -> np.ndarray:
        # cosine similarity: normalize vectors to unit length
        norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
        return vecs / norms

    def upsert(self, embeddings: List[List[float]], metadatas: List[Dict]):
        arr = np.array(embeddings, dtype="float32")
        arr = self._normalize(arr)
        self._ensure(arr.shape[1])
        self.index.add(arr)
        faiss.write_index(self.index, str(self.index_file))
        self._append_meta(metadatas)

    def search(self, query_emb: List[float], k: int = 5) -> List[Dict]:
        if self.index is None:
            return []
        q = np.array([query_emb], dtype="float32")
        q = self._normalize(q)
        D, I = self.index.search(q, k)
        results = []
        # read meta lines by index order
        metas = self.meta_file.read_text(encoding="utf-8").splitlines()
        for idx, score in zip(I[0], D[0]):
            if idx < 0 or idx >= len(metas):  # FAISS returns -1 if empty
                continue
            m = json.loads(metas[idx])
            m["score"] = float(score)
            results.append(m)
        return results
