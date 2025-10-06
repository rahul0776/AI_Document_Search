# backend/services/index_registry.py
from __future__ import annotations
from pathlib import Path
from typing import Dict
from retrieval.vector_store import FaissStore

class IndexRegistry:
    """
    Keeps one FaissStore per user_id rooted in: <root>/<user_id>/
    """
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, FaissStore] = {}

    def for_user(self, user_id: str) -> FaissStore:
        if user_id in self._cache:
            return self._cache[user_id]
        user_root = self.root / user_id
        user_root.mkdir(parents=True, exist_ok=True)
        store = FaissStore(str(user_root))
        self._cache[user_id] = store
        return store
