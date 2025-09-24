import fitz  # PyMuPDF
from pathlib import Path
import re
def extract_pdf_text(pdf_path: str) -> list[dict]:
    """
    Returns list of {page, text}. Empty text means likely scanned page (OCR later).
    """
    out = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        text = page.get_text("text") or ""
        out.append({"page": i + 1, "text": text})
    doc.close()
    return out

TITLE_LINE_RE = re.compile(r"^[^\w]*$")  # lines with only punctuation are not titles

def guess_title(pages: list[dict]) -> str | None:
    """
    Heuristics: first non-empty line on page 1 that
    - is short-ish (<= 90 chars),
    - has few trailing punctuation,
    - not all lowercase,
    - and not just punctuation.
    """
    if not pages:
        return None
    text = pages[0].get("text") or ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if len(line) > 90:
            continue
        if TITLE_LINE_RE.match(line):
            continue
        # reject lines that look like running headers/footers
        if re.search(r"page\s*\d+$", line, re.I):
            continue
        # prefer lines with capitals or title-case
        if line and (any(c.isupper() for c in line) or line.istitle()):
            return line
    return None