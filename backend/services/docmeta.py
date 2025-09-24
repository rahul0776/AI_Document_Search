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
        try:
            txt = self.meta_path.read_text(encoding="utf-8")
            return json.loads(txt or "[]")
        except Exception:
            return []

    def _write(self, items: List[Dict]):
        self.meta_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, doc_id: str, filename: str, pages: int = 0, title: str | None = None):
        """Idempotent upsert by doc_id."""
        items = self._read()
        now = datetime.utcnow().isoformat()
        found = False
        for it in items:
            if it.get("doc_id") == doc_id:
                it["filename"] = filename
                it["pages"] = pages
                it["title"] = title
                # keep original uploaded_at if present
                it.setdefault("uploaded_at", now)
                found = True
                break
        if not found:
            items.append({
                "doc_id": doc_id,
                "filename": filename,
                "pages": pages,
                "uploaded_at": now,
                "title": title,
            })
        self._write(items)

    def all(self) -> List[Dict]:
        return self._read()

    def delete(self, doc_id: str):
        items = self._read()
        items = [x for x in items if x.get("doc_id") != doc_id]
        self._write(items)
