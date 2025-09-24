from __future__ import annotations
from pathlib import Path
import json, faiss, numpy as np
from typing import List, Dict

class FaissStore:
    def __init__(self, index_dir: str):
        self.dir = Path(index_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.dir / "meta.jsonl"   # one json per row
        self.index_file = self.dir / "index.faiss"
        self.vec_file = self.dir / "vectors.npy"   # all vectors, row-aligned to meta.jsonl
        self.dim: int | None = None
        self.index = None
        self._metas: list[dict] = []               # in-memory metas
        self._vecs: np.ndarray | None = None       # in-memory vectors (N, D)
        self._load()

    # ---------- private helpers ----------
    def _load(self):
        # metas
        if self.meta_file.exists():
            with self.meta_file.open("r", encoding="utf-8") as f:
                self._metas = [json.loads(line) for line in f if line.strip()]
        else:
            self.meta_file.touch()
            self._metas = []

        # vectors
        if self.vec_file.exists():
            self._vecs = np.load(self.vec_file).astype("float32")
        else:
            self._vecs = None

        # index
        if self.index_file.exists():
            self.index = faiss.read_index(str(self.index_file))
            self.dim = self.index.d
        else:
            self.index = None
            self.dim = None

        # consistency check: meta rows == vector rows == index.ntotal
        m = len(self._metas)
        v = 0 if self._vecs is None else self._vecs.shape[0]
        n = 0 if self.index is None else int(getattr(self.index, "ntotal", 0))
        if not (m == v == n):
            # If mismatched, prefer the safest route: rebuild index from vectors+metas
            if self._vecs is not None and m == v and v > 0:
                self._rebuild_index(self._vecs)
            else:
                # Corrupt state → clear everything
                self.clear()

    def _ensure_index(self, dim: int):
        if self.index is None:
            self.index = faiss.IndexFlatIP(dim)  # cosine-like (normalize first)
            self.dim = dim

    @staticmethod
    def _normalize(vecs: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
        return vecs / norms

    def _persist_all(self):
        # write metas
        with self.meta_file.open("w", encoding="utf-8") as f:
            for it in self._metas:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        # write vectors
        if self._vecs is None:
            if self.vec_file.exists():
                self.vec_file.unlink(missing_ok=True)
        else:
            np.save(self.vec_file, self._vecs.astype("float32"))
        # write index from vectors
        if self._vecs is not None and self._vecs.size:
            self._rebuild_index(self._vecs)
        else:
            if self.index_file.exists():
                self.index_file.unlink(missing_ok=True)
            self.index = None
            self.dim = None

    def _rebuild_index(self, vecs: np.ndarray):
        if vecs is None or not vecs.size:
            self.index = None
            self.dim = None
            if self.index_file.exists():
                self.index_file.unlink(missing_ok=True)
            return
        vecs = vecs.astype("float32")
        vecs = self._normalize(vecs)
        self._ensure_index(vecs.shape[1])
        self.index.reset()
        self.index.add(vecs)
        faiss.write_index(self.index, str(self.index_file))

    # ---------- public API ----------
    def is_empty(self) -> bool:
        return (self.index is None) or (getattr(self.index, "ntotal", 0) == 0)

    def count(self) -> int:
        return 0 if self.index is None else int(getattr(self.index, "ntotal", 0))

    def clear(self):
        self._metas = []
        self._vecs = None
        self.index = None
        self.dim = None
        for p in (self.meta_file, self.vec_file, self.index_file):
            p.unlink(missing_ok=True)
        # recreate empty meta file
        self.meta_file.touch()

    def upsert(self, embeddings: List[List[float]], metadatas: List[Dict]):
        arr = np.array(embeddings, dtype="float32")
        arr = self._normalize(arr)
        self._ensure_index(arr.shape[1])

        # append in memory
        if self._vecs is None:
            self._vecs = arr
        else:
            self._vecs = np.vstack([self._vecs, arr])
        self._metas.extend(metadatas)

        # persist everything & rebuild FAISS
        self._persist_all()

    def search(self, query_emb: List[float], k: int = 5) -> List[Dict]:
        if self.index is None:
            return []
        q = np.array([query_emb], dtype="float32")
        q = self._normalize(q)
        D, I = self.index.search(q, k)
        results = []
        for idx, score in zip(I[0], D[0]):
            if idx < 0 or idx >= len(self._metas):
                continue
            m = dict(self._metas[idx])
            m["score"] = float(score)
            results.append(m)
        return results

    def delete_by_doc(self, doc_id: str):
        """Remove all rows for a doc_id (metas + vectors + index)."""
        if self.is_empty():
            return
        keep_idx = [i for i, m in enumerate(self._metas) if m.get("doc_id") != doc_id]
        if len(keep_idx) == len(self._metas):
            return  # nothing to delete
        # filter in memory
        self._metas = [self._metas[i] for i in keep_idx]
        if self._vecs is not None:
            self._vecs = self._vecs[keep_idx, :]
        # persist and rebuild
        self._persist_all()
