"""
Result fusion and re-ranking system for hybrid retrieval.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import math
from typing import List, Dict, Any, Tuple
import logging

from src.models.base import RetrievalResult, ProcessedChunk
from .interfaces import ReRankerInterface

logger = logging.getLogger(__name__)


class HybridReRanker(ReRankerInterface):
    """Re-ranker that combines multiple retrieval methods using RRF and metadata boosting."""
    
    def __init__(self, 
                 rrf_k: int = 60,
                 semantic_weight: float = 0.6,
                 keyword_weight: float = 0.4,
                 metadata_boost_factor: float = 1.2):
        """Initialize the hybrid re-ranker.
        
        Args:
            rrf_k: RRF parameter (typically 60)
            semantic_weight: Weight for semantic search results
            keyword_weight: Weight for keyword search results
            metadata_boost_factor: Boost factor for metadata-based scoring
        """
        self.rrf_k = rrf_k
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.metadata_boost_factor = metadata_boost_factor
        
        # Ensure weights sum to 1
        total_weight = semantic_weight + keyword_weight
        if total_weight != 1.0:
            self.semantic_weight = semantic_weight / total_weight
            self.keyword_weight = keyword_weight / total_weight
            logger.info(f"Normalized weights: semantic={self.semantic_weight:.3f}, "
                       f"keyword={self.keyword_weight:.3f}")
    
    def fuse_results_rrf(self, 
                        semantic_results: List[RetrievalResult], 
                        keyword_results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Fuse results using Reciprocal Rank Fusion (RRF).
        
        Args:
            semantic_results: Results from semantic search
            keyword_results: Results from keyword search
            
        Returns:
            Fused and re-ranked results
        """
        # Create mappings from chunk_id to rank for each method
        semantic_ranks = {result.chunk.chunk_id: i + 1 for i, result in enumerate(semantic_results)}
        keyword_ranks = {result.chunk.chunk_id: i + 1 for i, result in enumerate(keyword_results)}
        
        # Collect all unique chunks
        all_chunks = {}
        for result in semantic_results + keyword_results:
            chunk_id = result.chunk.chunk_id
            if chunk_id not in all_chunks:
                all_chunks[chunk_id] = result.chunk
        
        # Calculate RRF scores
        rrf_scores = {}
        for chunk_id in all_chunks:
            rrf_score = 0.0
            
            # Add semantic contribution
            if chunk_id in semantic_ranks:
                rrf_score += self.semantic_weight / (self.rrf_k + semantic_ranks[chunk_id])
            
            # Add keyword contribution
            if chunk_id in keyword_ranks:
                rrf_score += self.keyword_weight / (self.rrf_k + keyword_ranks[chunk_id])
            
            rrf_scores[chunk_id] = rrf_score
        
        # Create fused results
        fused_results = []
        for chunk_id, score in rrf_scores.items():
            # Get original scores for metadata
            semantic_score = None
            keyword_score = None
            
            for result in semantic_results:
                if result.chunk.chunk_id == chunk_id:
                    semantic_score = result.score
                    break
            
            for result in keyword_results:
                if result.chunk.chunk_id == chunk_id:
                    keyword_score = result.score
                    break
            
            fused_result = RetrievalResult(
                chunk=all_chunks[chunk_id],
                score=score,
                retrieval_method="hybrid_rrf",
                metadata={
                    "rrf_score": score,
                    "semantic_score": semantic_score,
                    "keyword_score": keyword_score,
                    "semantic_rank": semantic_ranks.get(chunk_id),
                    "keyword_rank": keyword_ranks.get(chunk_id),
                    "rrf_k": self.rrf_k,
                    "semantic_weight": self.semantic_weight,
                    "keyword_weight": self.keyword_weight
                }
            )
            fused_results.append(fused_result)
        
        # Sort by RRF score (descending)
        fused_results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Fused {len(semantic_results)} semantic + {len(keyword_results)} "
                   f"keyword results into {len(fused_results)} unique results")
        
        return fused_results
    
    def calculate_relevance_score(self, query: str, result: RetrievalResult) -> float:
        """Calculate enhanced relevance score combining multiple factors.
        
        Args:
            query: Original search query
            result: Retrieval result to score
            
        Returns:
            Enhanced relevance score
        """
        base_score = result.score
        
        # Apply metadata-based boosting
        metadata_boost = self._calculate_metadata_boost(query, result.chunk)
        
        # Apply content type boost
        content_type_boost = self._calculate_content_type_boost(query, result.chunk)
        
        # Apply position boost (earlier content is often more important)
        position_boost = self._calculate_position_boost(result.chunk)
        
        # Apply hierarchical context boost
        context_boost = self._calculate_context_boost(query, result.chunk)
        
        # Combine all factors
        enhanced_score = (base_score * 
                         metadata_boost * 
                         content_type_boost * 
                         position_boost * 
                         context_boost)
        
        return enhanced_score
    
    def _calculate_metadata_boost(self, query: str, chunk: ProcessedChunk) -> float:
        """Calculate boost based on chunk metadata.
        
        Args:
            query: Search query
            chunk: Document chunk
            
        Returns:
            Metadata boost factor
        """
        boost = 1.0
        query_lower = query.lower()
        
        # Boost based on topic relevance
        if "topic" in chunk.metadata:
            topic = chunk.metadata["topic"].lower()
            if any(term in topic for term in query_lower.split()):
                boost *= self.metadata_boost_factor
        
        # Boost based on difficulty level matching
        if "difficulty" in chunk.metadata:
            difficulty = chunk.metadata["difficulty"].lower()
            # Boost intermediate content slightly as it's often most useful
            if difficulty == "intermediate":
                boost *= 1.1
            # Boost advanced content for technical queries
            elif difficulty == "advanced" and self._is_technical_query(query):
                boost *= 1.15
        
        return boost
    
    def _calculate_content_type_boost(self, query: str, chunk: ProcessedChunk) -> float:
        """Calculate boost based on content type relevance to query.
        
        Args:
            query: Search query
            chunk: Document chunk
            
        Returns:
            Content type boost factor
        """
        query_lower = query.lower()
        
        # Boost formulas for mathematical queries
        if chunk.content_type.value == "formula":
            if any(term in query_lower for term in 
                   ["formula", "equation", "calculate", "capacity", "shannon", "snr", "bandwidth"]):
                return 1.3
            return 0.9  # Slight penalty if not math-related
        
        # Boost code for implementation queries
        elif chunk.content_type.value == "code":
            if any(term in query_lower for term in 
                   ["implement", "code", "algorithm", "python", "function", "bm25"]):
                return 1.25
            return 0.85  # Penalty if not code-related
        
        # Boost diagrams for visual/structural queries
        elif chunk.content_type.value == "diagram":
            if any(term in query_lower for term in 
                   ["diagram", "structure", "architecture", "flow", "model"]):
                return 1.2
            return 0.9
        
        # Text content is neutral
        return 1.0
    
    def _calculate_position_boost(self, chunk: ProcessedChunk) -> float:
        """Calculate boost based on position in document.
        
        Args:
            chunk: Document chunk
            
        Returns:
            Position boost factor
        """
        # Earlier content (introduction, overview) often more important
        position = chunk.position_in_document
        
        if position <= 0.1:  # First 10% of document
            return 1.15
        elif position <= 0.3:  # First 30% of document
            return 1.1
        elif position >= 0.9:  # Last 10% (often appendices, less important)
            return 0.9
        else:
            return 1.0
    
    def _calculate_context_boost(self, query: str, chunk: ProcessedChunk) -> float:
        """Calculate boost based on hierarchical context.
        
        Args:
            query: Search query
            chunk: Document chunk
            
        Returns:
            Context boost factor
        """
        boost = 1.0
        query_lower = query.lower()
        
        # Check if query terms appear in hierarchical context
        for context_level in chunk.hierarchical_context:
            context_lower = context_level.lower()
            if any(term in context_lower for term in query_lower.split()):
                boost *= 1.1  # Compound boost for multiple matches
        
        return min(boost, 1.5)  # Cap the boost to prevent over-boosting
    
    def _is_technical_query(self, query: str) -> bool:
        """Check if query appears to be technical in nature.
        
        Args:
            query: Search query
            
        Returns:
            True if query appears technical
        """
        technical_indicators = [
            "algorithm", "protocol", "implementation", "function", "method",
            "tcp", "ip", "http", "api", "database", "server", "client",
            "frequency", "bandwidth", "modulation", "signal", "antenna",
            "snr", "ber", "capacity", "throughput", "latency", "packet"
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in technical_indicators)
    
    def rerank(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Re-rank results using enhanced relevance scoring.
        
        Args:
            query: Original search query
            results: Results to re-rank
            
        Returns:
            Re-ranked results
        """
        if not results:
            return results
        
        # Calculate enhanced scores
        enhanced_results = []
        for result in results:
            enhanced_score = self.calculate_relevance_score(query, result)
            
            # Create new result with enhanced score
            enhanced_result = RetrievalResult(
                chunk=result.chunk,
                score=enhanced_score,
                retrieval_method=f"{result.retrieval_method}_reranked",
                metadata={
                    **result.metadata,
                    "original_score": result.score,
                    "enhanced_score": enhanced_score,
                    "boost_applied": enhanced_score / result.score if result.score > 0 else 1.0
                }
            )
            enhanced_results.append(enhanced_result)
        
        # Sort by enhanced score
        enhanced_results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Re-ranked {len(results)} results")
        return enhanced_results
    
    def calculate_diversity_score(self, results: List[RetrievalResult]) -> float:
        """Calculate diversity score for a set of results.
        
        Args:
            results: List of retrieval results
            
        Returns:
            Diversity score (0-1, higher is more diverse)
        """
        if len(results) <= 1:
            return 1.0
        
        # Check diversity across different dimensions
        content_types = set()
        documents = set()
        topics = set()
        difficulty_levels = set()
        
        for result in results:
            content_types.add(result.chunk.content_type.value)
            documents.add(result.chunk.document_id)
            
            if "topic" in result.chunk.metadata:
                topics.add(result.chunk.metadata["topic"])
            
            if "difficulty" in result.chunk.metadata:
                difficulty_levels.add(result.chunk.metadata["difficulty"])
        
        # Calculate diversity metrics
        content_type_diversity = len(content_types) / min(4, len(results))  # Max 4 content types
        document_diversity = len(documents) / len(results)
        topic_diversity = len(topics) / len(results) if topics else 0.5
        difficulty_diversity = len(difficulty_levels) / min(3, len(results))  # Max 3 levels
        
        # Weighted average of diversity metrics
        diversity_score = (
            0.3 * content_type_diversity +
            0.3 * document_diversity +
            0.2 * topic_diversity +
            0.2 * difficulty_diversity
        )
        
        return min(diversity_score, 1.0)
    
    def diversify_results(self, results: List[RetrievalResult], 
                         target_diversity: float = 0.7,
                         max_results: int = 10) -> List[RetrievalResult]:
        """Diversify results to avoid redundancy while maintaining relevance.
        
        Args:
            results: Input results sorted by relevance
            target_diversity: Target diversity score (0-1)
            max_results: Maximum number of results to return
            
        Returns:
            Diversified results
        """
        if len(results) <= max_results:
            return results
        
        diversified = []
        remaining = results.copy()
        
        # Always include the top result
        if remaining:
            diversified.append(remaining.pop(0))
        
        # Iteratively add results that improve diversity while maintaining relevance
        while len(diversified) < max_results and remaining:
            best_candidate = None
            best_score = -1
            
            for i, candidate in enumerate(remaining):
                # Calculate combined score: relevance + diversity improvement
                test_results = diversified + [candidate]
                diversity_score = self.calculate_diversity_score(test_results)
                
                # Weight relevance vs diversity (favor relevance more heavily)
                combined_score = 0.7 * candidate.score + 0.3 * diversity_score
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_candidate = i
            
            if best_candidate is not None:
                diversified.append(remaining.pop(best_candidate))
            else:
                break
        
        logger.info(f"Diversified {len(results)} results to {len(diversified)} "
                   f"with diversity score: {self.calculate_diversity_score(diversified):.3f}")
        
        return diversified