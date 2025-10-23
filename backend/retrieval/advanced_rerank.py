# backend/retrieval/advanced_rerank.py
"""
Advanced reranking using cross-encoder models.
Cross-encoders are more accurate than bi-encoders for final ranking.
"""
from __future__ import annotations
import logging
from typing import List, Dict
from sentence_transformers import CrossEncoder
import os

logger = logging.getLogger(__name__)


class AdvancedReranker:
    """
    Rerank search results using a cross-encoder model.
    
    Cross-encoders process query and document together, giving more
    accurate relevance scores than simple cosine similarity.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize reranker with a cross-encoder model.
        
        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        self.model = None
        self.enabled = os.getenv("ENABLE_RERANKING", "1") == "1"
        
        if self.enabled:
            try:
                logger.info(f"Loading cross-encoder model: {model_name}")
                self.model = CrossEncoder(model_name)
                logger.info("Cross-encoder loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load cross-encoder: {e}")
                self.enabled = False
                self.model = None
        else:
            logger.info("Reranking disabled via environment variable")
    
    def rerank(
        self, 
        query: str, 
        results: List[Dict],
        top_k: int = None
    ) -> List[Dict]:
        """
        Rerank results using cross-encoder.
        
        Args:
            query: Search query
            results: List of search results with 'text' field
            top_k: Optional limit on number of results to return
            
        Returns:
            Reranked results with 'rerank_score' added
        """
        if not self.enabled or not self.model or not results:
            return results
        
        try:
            # Prepare query-document pairs for cross-encoder
            pairs = [[query, result.get("text", "")] for result in results]
            
            # Get relevance scores from cross-encoder
            scores = self.model.predict(pairs)
            
            # Add rerank scores to results
            for result, score in zip(results, scores):
                result["rerank_score"] = float(score)
            
            # Sort by rerank score
            reranked = sorted(
                results, 
                key=lambda x: x.get("rerank_score", 0.0), 
                reverse=True
            )
            
            logger.info(f"Reranked {len(results)} results using cross-encoder")
            
            if top_k:
                reranked = reranked[:top_k]
            
            return reranked
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}, returning original results")
            return results
    
    def rerank_with_threshold(
        self,
        query: str,
        results: List[Dict],
        threshold: float = 0.0,
        top_k: int = None
    ) -> List[Dict]:
        """
        Rerank and filter results by relevance threshold.
        
        Args:
            query: Search query
            results: Search results
            threshold: Minimum relevance score (cross-encoder output)
            top_k: Maximum results to return
            
        Returns:
            Filtered and reranked results
        """
        reranked = self.rerank(query, results, top_k=None)
        
        # Filter by threshold
        filtered = [
            r for r in reranked 
            if r.get("rerank_score", 0.0) >= threshold
        ]
        
        logger.info(
            f"Filtered {len(reranked)} → {len(filtered)} results "
            f"with threshold {threshold}"
        )
        
        if top_k:
            filtered = filtered[:top_k]
        
        return filtered


# Global reranker instance
_reranker: AdvancedReranker | None = None

def get_reranker() -> AdvancedReranker:
    """Get or create the global reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = AdvancedReranker()
    return _reranker


def rerank_results(query: str, results: List[Dict], top_k: int = None) -> List[Dict]:
    """
    Convenience function to rerank results.
    
    Args:
        query: Search query
        results: Search results
        top_k: Optional limit
        
    Returns:
        Reranked results
    """
    reranker = get_reranker()
    return reranker.rerank(query, results, top_k=top_k)

