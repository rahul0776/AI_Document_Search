# backend/retrieval/hybrid_search.py
"""
Hybrid search combining semantic (vector) and keyword (BM25) search.
This provides better retrieval by leveraging both approaches.
"""
from __future__ import annotations
import logging
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
import numpy as np

logger = logging.getLogger(__name__)


class HybridSearcher:
    """
    Combines semantic search (FAISS) with keyword search (BM25) for better retrieval.
    
    Semantic search is good at understanding meaning and context.
    BM25 is good at exact keyword matching and rare terms.
    """
    
    def __init__(self, alpha: float = 0.5):
        """
        Initialize hybrid searcher.
        
        Args:
            alpha: Weight for semantic search (0-1). 
                   1.0 = pure semantic, 0.0 = pure BM25, 0.5 = balanced
        """
        self.alpha = alpha
        self.bm25 = None
        self.corpus_texts = []
        self.corpus_metadata = []
    
    def index_corpus(self, texts: List[str], metadata: List[Dict]):
        """
        Index a corpus of texts for BM25 search.
        
        Args:
            texts: List of text chunks
            metadata: List of metadata dicts (doc_id, page, etc.)
        """
        if not texts:
            logger.warning("Empty corpus provided to BM25 indexer")
            return
        
        self.corpus_texts = texts
        self.corpus_metadata = metadata
        
        # Tokenize texts for BM25
        tokenized_corpus = [text.lower().split() for text in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        logger.info(f"Indexed {len(texts)} documents for hybrid search")
    
    def search(
        self, 
        query: str, 
        semantic_results: List[Dict],
        top_k: int = 10
    ) -> List[Dict]:
        """
        Perform hybrid search combining semantic and keyword results.
        
        Args:
            query: Search query
            semantic_results: Results from FAISS semantic search
                             [{"text": "...", "score": 0.8, "doc_id": "...", ...}, ...]
            top_k: Number of results to return
            
        Returns:
            Combined and reranked results
        """
        if not self.bm25 or not self.corpus_texts:
            logger.warning("BM25 not initialized, returning semantic results only")
            return semantic_results[:top_k]
        
        # Get BM25 scores for all corpus documents
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # Normalize BM25 scores to 0-1 range
        if bm25_scores.max() > 0:
            bm25_scores_norm = bm25_scores / bm25_scores.max()
        else:
            bm25_scores_norm = bm25_scores
        
        # Create a mapping of text to BM25 score
        text_to_bm25 = {
            text: score 
            for text, score in zip(self.corpus_texts, bm25_scores_norm)
        }
        
        # Normalize semantic scores to 0-1 range
        semantic_scores = [hit.get("score", 0.0) for hit in semantic_results]
        if semantic_scores and max(semantic_scores) > 0:
            max_semantic = max(semantic_scores)
            for hit in semantic_results:
                hit["semantic_score"] = hit.get("score", 0.0) / max_semantic
        else:
            for hit in semantic_results:
                hit["semantic_score"] = 0.0
        
        # Combine scores using weighted average
        for hit in semantic_results:
            text = hit.get("text", "")
            bm25_score = text_to_bm25.get(text, 0.0)
            semantic_score = hit.get("semantic_score", 0.0)
            
            # Hybrid score: weighted combination
            hybrid_score = (self.alpha * semantic_score) + ((1 - self.alpha) * bm25_score)
            
            hit["bm25_score"] = float(bm25_score)
            hit["hybrid_score"] = float(hybrid_score)
        
        # Sort by hybrid score
        ranked_results = sorted(
            semantic_results, 
            key=lambda x: x.get("hybrid_score", 0.0), 
            reverse=True
        )
        
        logger.info(f"Hybrid search: combined {len(semantic_results)} semantic results with BM25")
        
        return ranked_results[:top_k]
    
    def clear(self):
        """Clear the indexed corpus."""
        self.bm25 = None
        self.corpus_texts = []
        self.corpus_metadata = []


# Global hybrid searcher instance
_hybrid_searcher: HybridSearcher | None = None

def get_hybrid_searcher(alpha: float = 0.5) -> HybridSearcher:
    """Get or create the global hybrid searcher instance."""
    global _hybrid_searcher
    if _hybrid_searcher is None:
        _hybrid_searcher = HybridSearcher(alpha=alpha)
    return _hybrid_searcher

