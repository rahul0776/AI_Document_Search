# backend/services/context_optimizer.py
"""
Context window optimization for better LLM responses.
Intelligently selects and formats the most relevant context for the LLM.
"""
from __future__ import annotations
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class ContextOptimizer:
    """
    Optimizes context selection and formatting for LLM prompts.
    
    Goals:
    1. Maximize relevance within token limits
    2. Provide diverse information (avoid redundancy)
    3. Maintain coherent context structure
    """
    
    def __init__(
        self,
        max_context_chunks: int = 5,
        max_chars_per_chunk: int = 1000,
        diversity_threshold: float = 0.3
    ):
        """
        Initialize context optimizer.
        
        Args:
            max_context_chunks: Maximum number of chunks to include
            max_chars_per_chunk: Max characters per chunk
            diversity_threshold: Minimum similarity for considering chunks redundant
        """
        self.max_context_chunks = max_context_chunks
        self.max_chars_per_chunk = max_chars_per_chunk
        self.diversity_threshold = diversity_threshold
    
    def optimize_context(
        self, 
        results: List[Dict],
        max_chunks: int = None
    ) -> List[Dict]:
        """
        Select optimal set of chunks for context.
        
        Args:
            results: List of retrieved chunks with scores
            max_chunks: Optional override for max chunks
            
        Returns:
            Optimized list of chunks
        """
        if not results:
            return []
        
        max_chunks = max_chunks or self.max_context_chunks
        
        # 1. Take top results
        top_results = results[:max_chunks * 2]  # Get more than needed for diversity filtering
        
        # 2. Remove very similar/redundant chunks
        diverse_results = self._filter_redundant(top_results)
        
        # 3. Limit to max chunks
        selected = diverse_results[:max_chunks]
        
        # 4. Truncate long chunks
        for result in selected:
            text = result.get("text", "")
            if len(text) > self.max_chars_per_chunk:
                result["text"] = text[:self.max_chars_per_chunk] + "..."
                result["truncated"] = True
        
        logger.info(
            f"Context optimization: {len(results)} → {len(selected)} chunks "
            f"(removed {len(results) - len(selected)} redundant/low-quality)"
        )
        
        return selected
    
    def _filter_redundant(self, results: List[Dict]) -> List[Dict]:
        """
        Filter out redundant/very similar chunks.
        
        Args:
            results: List of chunks
            
        Returns:
            Filtered list with diverse chunks
        """
        if len(results) <= 1:
            return results
        
        selected = [results[0]]  # Always keep the top result
        
        for result in results[1:]:
            text = result.get("text", "").lower()
            
            # Check if this result is too similar to already selected ones
            is_redundant = False
            for selected_result in selected:
                selected_text = selected_result.get("text", "").lower()
                
                # Simple redundancy check: high word overlap
                overlap = self._text_overlap(text, selected_text)
                
                if overlap > self.diversity_threshold:
                    is_redundant = True
                    logger.debug(f"Filtered redundant chunk (overlap: {overlap:.2f})")
                    break
            
            if not is_redundant:
                selected.append(result)
        
        return selected
    
    def _text_overlap(self, text1: str, text2: str) -> float:
        """
        Calculate word overlap between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Overlap ratio (0-1)
        """
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def format_context(
        self, 
        chunks: List[Dict],
        include_metadata: bool = True
    ) -> str:
        """
        Format optimized chunks into context string for LLM.
        
        Args:
            chunks: List of chunks to format
            include_metadata: Whether to include source metadata
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant context found."
        
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get("text", "")
            
            if include_metadata:
                doc_id = chunk.get("doc_id", "unknown")
                page = chunk.get("page", "?")
                score = chunk.get("hybrid_score") or chunk.get("rerank_score") or chunk.get("score", 0)
                
                header = f"[Source {i}: Document {doc_id}, Page {page}, Relevance: {score:.2f}]"
                context_parts.append(f"{header}\n{text}\n")
            else:
                context_parts.append(f"{text}\n")
        
        return "\n".join(context_parts)


# Global context optimizer
_context_optimizer: ContextOptimizer | None = None

def get_context_optimizer() -> ContextOptimizer:
    """Get or create global context optimizer instance."""
    global _context_optimizer
    if _context_optimizer is None:
        _context_optimizer = ContextOptimizer()
    return _context_optimizer

