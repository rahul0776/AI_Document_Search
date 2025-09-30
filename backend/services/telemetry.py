# backend/services/telemetry.py
from __future__ import annotations
from pathlib import Path
import json, time, os
from typing import Dict, Any

LOG_DIR = Path(os.getenv("LOG_DIR", "./data/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "events.jsonl"

def log_event(kind: str, payload: Dict[str, Any]) -> None:
    rec = {
        "ts": time.time(),
        "kind": kind,
        **payload,
    }
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        # Don't let logging break the app
        pass
