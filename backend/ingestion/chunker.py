# backend/ingestion/chunker.py
from typing import Iterable, List, Dict, Any
import re

def simple_sentence_split(text: str) -> List[str]:
    """Very light splitter; kept for compatibility."""
    sents = re.split(r'(?<=[\.\?\!])\s+', text.strip())
    return [s for s in sents if s]

# simple sentence split that prefers breaking after punctuation and before a new sentence start
SENT_SPLIT = re.compile(r"(?<=[.?!])\s+(?=[A-Z(])")

def smart_chunk_pages(
    pages: List[Any],            # accepts List[str] or List[Dict]
    target_chars: int = 900,
    overlap_chars: int = 120,
) -> Iterable[Dict]:
    """
    Paragraph → sentence packing. Keeps chunks near target size,
    overlaps by characters, and preserves page numbers.

    Accepts either:
      - List[str]  -> page numbers inferred from position (1-based)
      - List[Dict] -> expects {'text': str, 'page': int?}
    """
    for i, p in enumerate(pages, start=1):
        # normalize inputs
        if isinstance(p, str):
            page_no = i
            text = p
        elif isinstance(p, dict):
            page_no = int(p.get("page", i))
            text = (p.get("text") or "")
        else:
            # unknown item type; skip gracefully
            continue

        text = text.strip()
        if not text:
            continue

        # split by blank lines into paragraphs
        paragraphs = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]

        buf = ""
        for para in paragraphs:
            # if paragraph is large, split into sentences; otherwise keep as one unit
            sents = SENT_SPLIT.split(para) if len(para) > target_chars else [para]

            for s in sents:
                if not s:
                    continue
                if not buf:
                    buf = s
                elif len(buf) + 1 + len(s) <= target_chars:
                    buf += " " + s
                else:
                    # flush current buffer
                    yield {"text": buf, "page": page_no}

                    # create overlapping tail, then start next buffer with current sentence
                    if overlap_chars > 0 and len(buf) > overlap_chars:
                        buf = buf[-overlap_chars:] + " " + s
                    else:
                        buf = s

        if buf:
            yield {"text": buf, "page": page_no}
            buf = ""
