from ingestion.chunker import smart_chunk_pages

def test_chunker_basic():
    pages = ["Hello "*200, "World "*200]
    chunks = list(smart_chunk_pages(pages, target_chars=900, overlap_chars=120))
    assert len(chunks) >= 2
    assert all("text" in c and "page" in c for c in chunks)
