import fitz  # PyMuPDF
from pathlib import Path

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
