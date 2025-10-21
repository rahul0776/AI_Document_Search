# backend/services/index_registry.py
from __future__ import annotations
from pathlib import Path
from retrieval.vector_store import FaissStore

class IndexRegistry:
    """
    Simple per-user registry: each user gets its own FAISS index directory.
    """
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, FaissStore] = {}

    def for_user(self, user_id: str) -> FaissStore:
        if user_id not in self._cache:
            udir = self.root / user_id
            udir.mkdir(parents=True, exist_ok=True)
            self._cache[user_id] = FaissStore(str(udir))
        return self._cache[user_id]
