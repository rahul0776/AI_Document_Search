# backend/services/storage.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import threading

class LocalStorage:
    """
    Local disk storage, namespaced per user:
      uploads/{user_id}/{doc_id}.pdf
      uploads/{user_id}/docs.json
      uploads/{user_id}/queue.jsonl  (index jobs log)
    """

    # Serializes read-modify-write on docs.json across instances/threads.
    _LOCK = threading.RLock()

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ---------- Paths ----------
    def user_dir(self, user_id: str) -> Path:
        p = self.root / user_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def pdf_path(self, user_id: str, doc_id: str) -> Path:
        return self.user_dir(user_id) / f"{doc_id}.pdf"

    def meta_path(self, user_id: str) -> Path:
        return self.user_dir(user_id) / "docs.json"

    def queue_path(self, user_id: str) -> Path:
        return self.user_dir(user_id) / "queue.jsonl"

    # ---------- Metadata (docs.json) ----------
    def read_meta(self, user_id: str) -> List[Dict[str, Any]]:
        mp = self.meta_path(user_id)
        if not mp.exists():
            mp.write_text("[]", encoding="utf-8")
            return []
        try:
            return json.loads(mp.read_text(encoding="utf-8") or "[]")
        except Exception:
            return []

    def write_meta(self, user_id: str, rows: List[Dict[str, Any]]):
        mp = self.meta_path(user_id)
        mp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert_doc(self, user_id: str, doc: Dict[str, Any]):
        with self._LOCK:
            rows = self.read_meta(user_id)
            rows = [x for x in rows if x.get("doc_id") != doc.get("doc_id")]
            rows.append(doc)
            self.write_meta(user_id, rows)

    def delete_doc_meta(self, user_id: str, doc_id: str):
        with self._LOCK:
            rows = self.read_meta(user_id)
            rows = [x for x in rows if x.get("doc_id") != doc_id]
            self.write_meta(user_id, rows)

    # ---------- Queue (best-effort log of index jobs) ----------
    def append_queue(self, user_id: str, item: Dict[str, Any]):
        qp = self.queue_path(user_id)
        with self._LOCK:
            with qp.open("a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
