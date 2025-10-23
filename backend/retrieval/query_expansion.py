# backend/retrieval/query_expansion.py
"""
Query expansion to improve retrieval by generating related search terms.
Helps find relevant documents even when query wording differs from document text.
"""
from __future__ import annotations
import logging
from typing import List, Set
import re

logger = logging.getLogger(__name__)


class QueryExpander:
    """
    Expands user queries with synonyms and related terms.
    
    Simple but effective approach using:
    1. Common business/technical synonyms
    2. Acronym expansion
    3. Related term patterns
    """
    
    # Common synonym mappings
    SYNONYMS = {
        "cost": ["price", "expense", "fee", "charge"],
        "benefit": ["advantage", "pro", "positive", "plus"],
        "disadvantage": ["drawback", "con", "negative", "downside"],
        "increase": ["rise", "grow", "boost", "escalate"],
        "decrease": ["decline", "drop", "reduce", "fall"],
        "start": ["begin", "initiate", "commence", "launch"],
        "end": ["finish", "conclude", "complete", "terminate"],
        "important": ["critical", "crucial", "vital", "key"],
        "problem": ["issue", "challenge", "difficulty", "concern"],
        "solution": ["answer", "resolution", "fix", "remedy"],
        "method": ["approach", "technique", "process", "way"],
        "result": ["outcome", "consequence", "effect", "impact"],
        "show": ["demonstrate", "display", "illustrate", "present"],
        "explain": ["describe", "clarify", "detail", "elaborate"],
        "compare": ["contrast", "differentiate", "distinguish", "vs"],
    }
    
    # Common acronyms and their expansions
    ACRONYMS = {
        "ai": "artificial intelligence",
        "ml": "machine learning",
        "nlp": "natural language processing",
        "api": "application programming interface",
        "ui": "user interface",
        "ux": "user experience",
        "roi": "return on investment",
        "kpi": "key performance indicator",
        "ceo": "chief executive officer",
        "cto": "chief technology officer",
        "qa": "quality assurance",
        "sla": "service level agreement",
    }
    
    def __init__(self, max_expansions: int = 3):
        """
        Initialize query expander.
        
        Args:
            max_expansions: Maximum number of expansion terms to add per word
        """
        self.max_expansions = max_expansions
    
    def expand_query(self, query: str) -> str:
        """
        Expand a query with synonyms and related terms.
        
        Args:
            query: Original search query
            
        Returns:
            Expanded query string with additional terms
        """
        if not query:
            return query
        
        original_query = query
        expanded_terms = set([query.lower()])
        
        # Tokenize query
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Add acronym expansions
        for word in words:
            if word in self.ACRONYMS:
                expansion = self.ACRONYMS[word]
                expanded_terms.add(expansion)
                logger.debug(f"Expanded acronym: {word} → {expansion}")
        
        # Add synonyms
        for word in words:
            if word in self.SYNONYMS:
                synonyms = self.SYNONYMS[word][:self.max_expansions]
                expanded_terms.update(synonyms)
                logger.debug(f"Added synonyms for {word}: {synonyms}")
        
        # Combine original query with expansions
        if len(expanded_terms) > 1:
            # Keep original query first, then add expansions
            expanded_query = f"{original_query} {' '.join(expanded_terms - {query.lower()})}"
            logger.info(f"Query expanded: '{original_query}' → '{expanded_query}'")
            return expanded_query
        
        return original_query
    
    def extract_key_terms(self, query: str) -> List[str]:
        """
        Extract key terms from a query (useful for highlighting).
        
        Args:
            query: Search query
            
        Returns:
            List of key terms
        """
        # Remove common stop words
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "should", "could", "may", "might", "can", "of", "in",
            "on", "at", "to", "for", "with", "by", "from", "about"
        }
        
        words = re.findall(r'\b\w+\b', query.lower())
        key_terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        return key_terms


# Global query expander instance
_query_expander: QueryExpander | None = None

def get_query_expander() -> QueryExpander:
    """Get or create the global query expander instance."""
    global _query_expander
    if _query_expander is None:
        _query_expander = QueryExpander()
    return _query_expander


def expand_query_simple(query: str, max_expansions: int = 3) -> str:
    """
    Simple function to expand a query.
    
    Args:
        query: Original query
        max_expansions: Max synonyms per word
        
    Returns:
        Expanded query
    """
    expander = get_query_expander()
    return expander.expand_query(query)

