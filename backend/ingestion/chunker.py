from typing import Iterable, List, Dict
import re
def simple_sentence_split(text: str) -> List[str]:
    # very light splitter; we'll chunk over this
    import re
    sents = re.split(r'(?<=[\.\?\!])\s+', text.strip())
    return [s for s in sents if s]

SENT_SPLIT = re.compile(r"(?<=[.?!])\s+(?=[A-Z(])")  # simple sentence split

def smart_chunk_pages(
    pages: List[Dict],
    target_chars: int = 900,
    overlap_chars: int = 120,
) -> Iterable[Dict]:
    """
    Paragraph → sentence packing. Keeps chunks near target size,
    overlaps by characters, and preserves page numbers.
    """
    for p in pages:
        page_no = p.get("page", 1)
        text = (p.get("text") or "").strip()
        if not text:
            continue

        # split by blank lines first
        paragraphs = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
        buf = ""
        for para in paragraphs:
            # break para into sentences if it's too big
            sents = SENT_SPLIT.split(para) if len(para) > target_chars else [para]
            for s in sents:
                if not buf:
                    buf = s
                elif len(buf) + 1 + len(s) <= target_chars:
                    buf += " " + s
                else:
                    yield {"text": buf, "page": page_no}
                    # overlap tail
                    if overlap_chars > 0 and len(buf) > overlap_chars:
                        buf = buf[-overlap_chars:] + " " + s
                    else:
                        buf = s
        if buf:
            yield {"text": buf, "page": page_no}
            buf = ""
