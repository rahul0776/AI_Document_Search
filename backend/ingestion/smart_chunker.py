# backend/ingestion/smart_chunker.py
"""
Improved chunking strategy with overlapping windows and semantic splitting.
Better chunking = better retrieval = better answers.
"""
from __future__ import annotations
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class SmartChunker:
    """
    Intelligent text chunker that:
    1. Respects sentence boundaries
    2. Uses overlapping windows for context continuity
    3. Handles different document structures
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        min_chunk_size: int = 50
    ):
        """
        Initialize smart chunker.
        
        Args:
            chunk_size: Target size for each chunk (in characters)
            chunk_overlap: Overlap between consecutive chunks
            min_chunk_size: Minimum size for a valid chunk
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences, handling edge cases.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Handle common abbreviations
        text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr)\\.', r'\1<PERIOD>', text)
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Restore abbreviations
        sentences = [s.replace('<PERIOD>', '.') for s in sentences]
        
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Chunk text into overlapping windows that respect sentence boundaries.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to each chunk (doc_id, page, etc.)
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text or len(text) < self.min_chunk_size:
            logger.warning(f"Text too small to chunk: {len(text)} chars")
            return []
        
        metadata = metadata or {}
        sentences = self.split_into_sentences(text)
        
        if not sentences:
            # Fallback to simple splitting if sentence detection fails
            return self._fallback_chunk(text, metadata)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence exceeds chunk size, create a new chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "sentence_count": len(current_chunk),
                    **metadata
                })
                
                # Keep last few sentences for overlap
                overlap_text = ' '.join(current_chunk)
                overlap_sentences = []
                overlap_length = 0
                
                # Add sentences from the end until we reach overlap size
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append({
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "sentence_count": len(current_chunk),
                    **metadata
                })
        
        logger.info(f"Created {len(chunks)} chunks from {len(sentences)} sentences")
        return chunks
    
    def _fallback_chunk(self, text: str, metadata: Dict) -> List[Dict]:
        """
        Fallback chunking strategy using simple character windows.
        
        Args:
            text: Input text
            metadata: Metadata for chunks
            
        Returns:
            List of chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at word boundary
            if end < len(text):
                # Look for space within next 50 characters
                space_pos = text.find(' ', end, end + 50)
                if space_pos != -1:
                    end = space_pos
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append({
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    **metadata
                })
            
            # Move start position with overlap
            start = end - self.chunk_overlap
        
        return chunks


def chunk_documents_smart(
    documents: List[Dict[str, str]], 
    chunk_size: int = 500,
    chunk_overlap: int = 100
) -> List[Dict]:
    """
    Chunk multiple documents using smart chunking strategy.
    
    Args:
        documents: List of documents with 'text', 'doc_id', 'page' fields
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunks with metadata
    """
    chunker = SmartChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    all_chunks = []
    
    for doc in documents:
        text = doc.get("text", "")
        metadata = {
            "doc_id": doc.get("doc_id", "unknown"),
            "page": doc.get("page", 0),
            "title": doc.get("title", ""),
        }
        
        chunks = chunker.chunk_text(text, metadata)
        all_chunks.extend(chunks)
    
    logger.info(f"Smart chunking: {len(documents)} docs → {len(all_chunks)} chunks")
    return all_chunks

