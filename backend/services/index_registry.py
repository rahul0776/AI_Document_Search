# backend/services/index_registry.py
from __future__ import annotations
from pathlib import Path
from typing import Dict
from retrieval.vector_store import FaissStore

class IndexRegistry:
    """
    Keeps one FAISS index per user in {index_root}/{user_id}.
    """
    def __init__(self, index_root: str):
        self.root = Path(index_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, FaissStore] = {}

    def for_user(self, user_id: str) -> FaissStore:
        if user_id not in self._cache:
            path = self.root / user_id
            path.mkdir(parents=True, exist_ok=True)
            self._cache[user_id] = FaissStore(str(path))
        return self._cache[user_id]
