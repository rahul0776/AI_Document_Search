# backend/services/rag_evaluator.py
"""
Simple RAG evaluation metrics to track answer quality.
Helps measure improvements from advanced RAG techniques.
"""
from __future__ import annotations
import logging
from typing import List, Dict
import time
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """
    Track and evaluate RAG performance metrics.
    
    Metrics tracked:
    - Retrieval quality (scores, diversity)
    - Response latency
    - Context utilization
    """
    
    def __init__(self, log_dir: str = "./data/logs"):
        """
        Initialize RAG evaluator.
        
        Args:
            log_dir: Directory to store evaluation logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.log_dir / "rag_metrics.jsonl"
    
    def log_retrieval(
        self,
        query: str,
        results_count: int,
        avg_score: float,
        retrieval_time: float,
        method: str = "standard"
    ):
        """
        Log retrieval metrics.
        
        Args:
            query: Search query
            results_count: Number of results retrieved
            avg_score: Average relevance score
            retrieval_time: Time taken for retrieval (seconds)
            method: Retrieval method used (standard, hybrid, etc.)
        """
        metric = {
            "timestamp": time.time(),
            "type": "retrieval",
            "query": query,
            "results_count": results_count,
            "avg_score": avg_score,
            "retrieval_time_ms": int(retrieval_time * 1000),
            "method": method
        }
        
        self._write_metric(metric)
    
    def log_generation(
        self,
        query: str,
        context_chunks: int,
        context_chars: int,
        generation_time: float,
        tokens_generated: int = None
    ):
        """
        Log answer generation metrics.
        
        Args:
            query: Original query
            context_chunks: Number of context chunks used
            context_chars: Total context characters
            generation_time: Time for generation (seconds)
            tokens_generated: Optional token count
        """
        metric = {
            "timestamp": time.time(),
            "type": "generation",
            "query": query,
            "context_chunks": context_chunks,
            "context_chars": context_chars,
            "generation_time_ms": int(generation_time * 1000),
            "tokens_generated": tokens_generated
        }
        
        self._write_metric(metric)
    
    def log_full_rag_cycle(
        self,
        query: str,
        retrieval_metrics: Dict,
        generation_metrics: Dict,
        total_time: float
    ):
        """
        Log complete RAG cycle metrics.
        
        Args:
            query: User query
            retrieval_metrics: Metrics from retrieval phase
            generation_metrics: Metrics from generation phase
            total_time: Total end-to-end time (seconds)
        """
        metric = {
            "timestamp": time.time(),
            "type": "full_rag_cycle",
            "query": query,
            "retrieval": retrieval_metrics,
            "generation": generation_metrics,
            "total_time_ms": int(total_time * 1000)
        }
        
        self._write_metric(metric)
    
    def _write_metric(self, metric: Dict):
        """Write metric to log file."""
        try:
            with self.metrics_file.open("a") as f:
                f.write(json.dumps(metric) + "\n")
        except Exception as e:
            logger.error(f"Failed to write metric: {e}")
    
    def get_summary_stats(self, last_n: int = 100) -> Dict:
        """
        Get summary statistics from recent metrics.
        
        Args:
            last_n: Number of recent metrics to analyze
            
        Returns:
            Dictionary of summary statistics
        """
        if not self.metrics_file.exists():
            return {}
        
        try:
            metrics = []
            with self.metrics_file.open("r") as f:
                for line in f:
                    try:
                        metrics.append(json.loads(line))
                    except:
                        continue
            
            # Take last N metrics
            recent = metrics[-last_n:]
            
            if not recent:
                return {}
            
            # Calculate stats
            retrieval_times = [
                m["retrieval_time_ms"] 
                for m in recent 
                if m.get("type") == "retrieval"
            ]
            
            generation_times = [
                m["generation_time_ms"]
                for m in recent
                if m.get("type") == "generation"
            ]
            
            avg_scores = [
                m["avg_score"]
                for m in recent
                if m.get("type") == "retrieval" and "avg_score" in m
            ]
            
            return {
                "total_queries": len(recent),
                "avg_retrieval_time_ms": sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0,
                "avg_generation_time_ms": sum(generation_times) / len(generation_times) if generation_times else 0,
                "avg_relevance_score": sum(avg_scores) / len(avg_scores) if avg_scores else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to generate summary stats: {e}")
            return {}


# Global evaluator
_evaluator: RAGEvaluator | None = None

def get_evaluator() -> RAGEvaluator:
    """Get or create global evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = RAGEvaluator()
    return _evaluator

