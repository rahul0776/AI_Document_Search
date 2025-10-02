# backend/services/docmeta.py
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

class DocMetaStore:
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.meta_path = self.root / "docs.json"
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.meta_path.exists():
            self.meta_path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict]:
        txt = self.meta_path.read_text(encoding="utf-8") or "[]"
        try:
            return json.loads(txt)
        except Exception:
            return []

    def _write(self, items: List[Dict]):
        self.meta_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, user_id: str, doc_id: str, filename: str, pages: int = 0, title: str | None = None):
        items = self._read()
        now = datetime.utcnow().isoformat()
        # upsert by (user_id, doc_id)
        found = False
        for it in items:
            if it.get("user_id") == user_id and it.get("doc_id") == doc_id:
                it.update({"filename": filename, "pages": pages, "title": title, "uploaded_at": it.get("uploaded_at", now)})
                found = True
                break
        if not found:
            items.append({
                "user_id": user_id,
                "doc_id": doc_id,
                "filename": filename,
                "pages": pages,
                "uploaded_at": now,
                "title": title,
            })
        self._write(items)

    def all_for_user(self, user_id: str) -> List[Dict]:
        return [x for x in self._read() if x.get("user_id") == user_id]

    def delete(self, user_id: str, doc_id: str):
        items = self._read()
        items = [x for x in items if not (x.get("user_id") == user_id and x.get("doc_id") == doc_id)]
        self._write(items)
