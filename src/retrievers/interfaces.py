"""
Abstract interfaces for retrieval components.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from src.models.base import RetrievalResult, ProcessedChunk, EnhancedQuery


class RetrieverInterface(ABC):
    """Abstract interface for document retrievers."""
    
    @abstractmethod
    def retrieve(self, query: str, filters: Dict[str, Any], k: int = 10) -> List[RetrievalResult]:
        """Retrieve relevant documents for a query."""
        pass
    
    @abstractmethod
    def setup_index(self, chunks: List[ProcessedChunk]) -> None:
        """Set up the retrieval index."""
        pass


class SemanticRetrieverInterface(RetrieverInterface):
    """Abstract interface for semantic retrieval."""
    
    @abstractmethod
    def semantic_search(self, query: str, k: int) -> List[RetrievalResult]:
        """Perform semantic similarity search."""
        pass


class KeywordRetrieverInterface(RetrieverInterface):
    """Abstract interface for keyword-based retrieval."""
    
    @abstractmethod
    def keyword_search(self, query: str, k: int) -> List[RetrievalResult]:
        """Perform keyword-based search."""
        pass
    
    @abstractmethod
    def build_inverted_index(self, chunks: List[ProcessedChunk]) -> None:
        """Build inverted index for keyword search."""
        pass


class HybridRetrieverInterface(RetrieverInterface):
    """Abstract interface for hybrid retrieval."""
    
    @abstractmethod
    def fuse_results(self, semantic_results: List[RetrievalResult], 
                    keyword_results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Fuse results from multiple retrieval methods."""
        pass


class ReRankerInterface(ABC):
    """Abstract interface for result re-ranking."""
    
    @abstractmethod
    def rerank(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Re-rank retrieval results."""
        pass
    
    @abstractmethod
    def calculate_relevance_score(self, query: str, result: RetrievalResult) -> float:
        """Calculate relevance score for a result."""
        pass


class QueryEnhancerInterface(ABC):
    """Abstract interface for query enhancement."""
    
    @abstractmethod
    def enhance_query(self, query: str, context: Dict[str, Any]) -> EnhancedQuery:
        """Enhance a query with expansion and correction."""
        pass
    
    @abstractmethod
    def expand_terms(self, query: str) -> List[str]:
        """Expand query terms with synonyms."""
        pass
    
    @abstractmethod
    def correct_spelling(self, query: str) -> str:
        """Correct spelling in query."""
        pass
    
    @abstractmethod
    def detect_ambiguity(self, query: str) -> Dict[str, Any]:
        """Detect ambiguity in query."""
        pass