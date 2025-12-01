"""
BM25 keyword search implementation for the RAG system.
"""
import re
import string
from typing import List, Dict, Any, Set
from collections import defaultdict
import logging

from rank_bm25 import BM25Okapi
from models.base import ProcessedChunk, RetrievalResult
from retrievers.interfaces import KeywordRetrieverInterface

logger = logging.getLogger(__name__)


class BM25Retriever(KeywordRetrieverInterface):
    """BM25-based keyword retrieval implementation."""
    
    def __init__(self, language: str = "en"):
        """Initialize BM25 retriever.
        
        Args:
            language: Language for text processing (default: "en")
        """
        self.language = language
        self.bm25_index = None
        self.chunks = []
        self.inverted_index = defaultdict(set)
        self.stopwords = self._get_stopwords()
        
    def _get_stopwords(self) -> Set[str]:
        """Get stopwords for the specified language."""
        # Basic English stopwords - in production, use NLTK or spaCy
        english_stopwords = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'would', 'could', 'should', 'may',
            'might', 'can', 'must', 'shall', 'this', 'these', 'those', 'they',
            'them', 'their', 'there', 'where', 'when', 'what', 'who', 'why',
            'how', 'i', 'you', 'we', 'us', 'our', 'your', 'his', 'her', 'him'
        }
        
        # Add French stopwords for multilingual support
        french_stopwords = {
            'le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir',
            'que', 'pour', 'dans', 'ce', 'son', 'une', 'sur', 'avec', 'ne',
            'se', 'pas', 'tout', 'plus', 'par', 'grand', 'en', 'me', 'bien',
            'où', 'ou', 'si', 'les', 'du', 'des', 'la', 'au', 'aux', 'cette',
            'ces', 'ses', 'nos', 'vos', 'leurs', 'mais', 'donc', 'car', 'ni'
        }
        
        return english_stopwords.union(french_stopwords)
    
    def _preprocess_text(self, text: str) -> List[str]:
        """Preprocess text for BM25 indexing.
        
        Args:
            text: Raw text to preprocess
            
        Returns:
            List of preprocessed tokens
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation except for mathematical symbols and technical terms
        # Keep dots in decimal numbers and technical abbreviations
        text = re.sub(r'[^\w\s\.\-]', ' ', text)
        
        # Split into tokens
        tokens = text.split()
        
        # Filter tokens
        processed_tokens = []
        for token in tokens:
            # Remove pure punctuation tokens
            if token.strip(string.punctuation):
                # Keep tokens that are not stopwords or are technical terms
                if (token not in self.stopwords or 
                    self._is_technical_term(token) or 
                    len(token) > 10):  # Keep long words even if they're stopwords
                    processed_tokens.append(token)
        
        return processed_tokens
    
    def _is_technical_term(self, token: str) -> bool:
        """Check if a token is likely a technical term.
        
        Args:
            token: Token to check
            
        Returns:
            True if token appears to be technical
        """
        # Technical indicators
        technical_patterns = [
            r'\d+',  # Contains numbers
            r'[A-Z]{2,}',  # Multiple uppercase letters (acronyms)
            r'.*[_\-].*',  # Contains underscores or hyphens
            r'.*\.(com|org|net|edu)',  # URLs
            r'.*@.*',  # Email-like
        ]
        
        for pattern in technical_patterns:
            if re.search(pattern, token):
                return True
                
        # Technical domains (extend as needed)
        technical_domains = {
            'tcp', 'ip', 'http', 'https', 'ftp', 'ssh', 'ssl', 'tls',
            'wifi', 'bluetooth', 'ethernet', 'lan', 'wan', 'vpn',
            'api', 'json', 'xml', 'html', 'css', 'javascript', 'python',
            'algorithm', 'database', 'server', 'client', 'protocol',
            'frequency', 'amplitude', 'modulation', 'signal', 'antenna',
            'bandwidth', 'throughput', 'latency', 'packet', 'frame'
        }
        
        return token.lower() in technical_domains
    
    def build_inverted_index(self, chunks: List[ProcessedChunk]) -> None:
        """Build inverted index for efficient keyword matching.
        
        Args:
            chunks: List of processed document chunks
        """
        logger.info(f"Building inverted index for {len(chunks)} chunks")
        
        self.inverted_index.clear()
        
        for i, chunk in enumerate(chunks):
            tokens = self._preprocess_text(chunk.content)
            
            # Add tokens to inverted index
            for token in set(tokens):  # Use set to avoid duplicate entries
                self.inverted_index[token].add(i)
        
        logger.info(f"Inverted index built with {len(self.inverted_index)} unique terms")
    
    def setup_index(self, chunks: List[ProcessedChunk]) -> None:
        """Set up the BM25 retrieval index.
        
        Args:
            chunks: List of processed document chunks
        """
        logger.info(f"Setting up BM25 index for {len(chunks)} chunks")
        
        self.chunks = chunks
        
        # Preprocess all chunk content for BM25
        tokenized_chunks = []
        for chunk in chunks:
            tokens = self._preprocess_text(chunk.content)
            tokenized_chunks.append(tokens)
        
        # Build BM25 index
        self.bm25_index = BM25Okapi(tokenized_chunks)
        
        # Build inverted index for additional functionality
        self.build_inverted_index(chunks)
        
        logger.info("BM25 index setup completed")
    
    def keyword_search(self, query: str, k: int) -> List[RetrievalResult]:
        """Perform keyword-based search using BM25.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of retrieval results sorted by BM25 score
        """
        if not self.bm25_index or not self.chunks:
            logger.warning("BM25 index not initialized")
            return []
        
        # Preprocess query
        query_tokens = self._preprocess_text(query)
        
        if not query_tokens:
            logger.warning("No valid tokens in query after preprocessing")
            return []
        
        # Get BM25 scores
        scores = self.bm25_index.get_scores(query_tokens)
        
        # Create results with scores
        results = []
        for i, score in enumerate(scores):
            if score > 0:  # Only include results with positive scores
                result = RetrievalResult(
                    chunk=self.chunks[i],
                    score=float(score),
                    retrieval_method="keyword_bm25",
                    metadata={
                        "query_tokens": query_tokens,
                        "matched_terms": self._get_matched_terms(query_tokens, i),
                        "bm25_score": float(score)
                    }
                )
                results.append(result)
        
        # Sort by score (descending) and return top k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]
    
    def _get_matched_terms(self, query_tokens: List[str], chunk_index: int) -> List[str]:
        """Get terms that matched between query and chunk.
        
        Args:
            query_tokens: Preprocessed query tokens
            chunk_index: Index of the chunk
            
        Returns:
            List of matched terms
        """
        if chunk_index >= len(self.chunks):
            return []
        
        chunk_tokens = set(self._preprocess_text(self.chunks[chunk_index].content))
        matched_terms = [token for token in query_tokens if token in chunk_tokens]
        return matched_terms
    
    def retrieve(self, query: str, filters: Dict[str, Any], k: int = 10) -> List[RetrievalResult]:
        """Retrieve relevant documents for a query with optional filters.
        
        Args:
            query: Search query
            filters: Metadata filters to apply
            k: Number of results to return
            
        Returns:
            List of filtered retrieval results
        """
        # Get initial results from keyword search
        results = self.keyword_search(query, k * 2)  # Get more results for filtering
        
        # Apply filters if provided
        if filters:
            filtered_results = []
            for result in results:
                if self._matches_filters(result.chunk, filters):
                    filtered_results.append(result)
            results = filtered_results
        
        return results[:k]
    
    def _matches_filters(self, chunk: ProcessedChunk, filters: Dict[str, Any]) -> bool:
        """Check if a chunk matches the provided filters.
        
        Args:
            chunk: Document chunk to check
            filters: Filters to apply
            
        Returns:
            True if chunk matches all filters
        """
        for key, value in filters.items():
            if key == "document_type":
                # Check document metadata (would need to be loaded separately)
                continue
            elif key == "content_type":
                if chunk.content_type.value != value:
                    return False
            elif key == "page_number":
                if isinstance(value, dict):
                    if "min" in value and chunk.page_number < value["min"]:
                        return False
                    if "max" in value and chunk.page_number > value["max"]:
                        return False
                elif chunk.page_number != value:
                    return False
            elif key in chunk.metadata:
                if chunk.metadata[key] != value:
                    return False
        
        return True
    
    def get_term_frequency(self, term: str) -> int:
        """Get frequency of a term across all documents.
        
        Args:
            term: Term to look up
            
        Returns:
            Number of documents containing the term
        """
        processed_term = self._preprocess_text(term)
        if not processed_term:
            return 0
        
        term_key = processed_term[0]
        return len(self.inverted_index.get(term_key, set()))
    
    def get_similar_terms(self, term: str, max_results: int = 5) -> List[str]:
        """Get terms similar to the input term (basic implementation).
        
        Args:
            term: Input term
            max_results: Maximum number of similar terms to return
            
        Returns:
            List of similar terms
        """
        processed_term = self._preprocess_text(term)
        if not processed_term:
            return []
        
        term_key = processed_term[0].lower()
        similar_terms = []
        
        # Simple similarity based on string matching
        for indexed_term in self.inverted_index.keys():
            if (indexed_term != term_key and 
                (term_key in indexed_term or indexed_term in term_key or
                 self._levenshtein_distance(term_key, indexed_term) <= 2)):
                similar_terms.append(indexed_term)
        
        return similar_terms[:max_results]
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Levenshtein distance
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]