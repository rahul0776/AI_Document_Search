from typing import Iterable, List, Dict

def simple_sentence_split(text: str) -> List[str]:
    # very light splitter; we'll chunk over this
    import re
    sents = re.split(r'(?<=[\.\?\!])\s+', text.strip())
    return [s for s in sents if s]

def chunk_pages(pages: Iterable[Dict], chunk_chars: int = 1200, overlap: int = 150):
    """
    Yields chunks: {text, page}
    Keeps chunks around ~1200 chars with small overlap, respecting sentence boundaries.
    """
    for p in pages:
        sents = simple_sentence_split(p["text"])
        buf = []
        size = 0
        for s in sents:
            if size + len(s) > chunk_chars and buf:
                chunk_text = " ".join(buf).strip()
                if chunk_text:
                    yield {"text": chunk_text, "page": p["page"]}
                # start next with overlap from end
                overlap_text = " ".join(buf)[-overlap:]
                buf = [overlap_text, s] if overlap_text else [s]
                size = len(" ".join(buf))
            else:
                buf.append(s)
                size += len(s)
        if buf:
            chunk_text = " ".join(buf).strip()
            if chunk_text:
                yield {"text": chunk_text, "page": p["page"]}
