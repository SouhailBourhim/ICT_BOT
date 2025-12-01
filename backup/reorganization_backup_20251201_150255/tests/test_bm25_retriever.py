"""
Unit tests for BM25 keyword search retriever.
"""
import unittest
from datetime import datetime
from typing import List

from models.base import ProcessedChunk, ContentType, RetrievalResult
from retrievers.bm25_retriever import BM25Retriever


class TestBM25Retriever(unittest.TestCase):
    """Test cases for BM25Retriever."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retriever = BM25Retriever()
        
        # Create test chunks
        self.test_chunks = [
            ProcessedChunk(
                chunk_id="chunk_1",
                document_id="doc_1",
                content="Wireless communication systems use electromagnetic waves to transmit information. "
                       "The frequency spectrum is divided into different bands for various applications.",
                content_type=ContentType.TEXT,
                hierarchical_context=["Chapter 1", "Introduction"],
                page_number=1,
                position_in_document=0.1,
                metadata={"topic": "wireless_communication", "difficulty": "basic"}
            ),
            ProcessedChunk(
                chunk_id="chunk_2",
                document_id="doc_1",
                content="Rayleigh fading occurs in wireless channels when there is no direct line-of-sight "
                       "between transmitter and receiver. The signal amplitude follows a Rayleigh distribution.",
                content_type=ContentType.TEXT,
                hierarchical_context=["Chapter 2", "Fading Channels"],
                page_number=15,
                position_in_document=0.3,
                metadata={"topic": "fading", "difficulty": "intermediate"}
            ),
            ProcessedChunk(
                chunk_id="chunk_3",
                document_id="doc_2",
                content="TCP/IP protocol stack consists of four layers: Application, Transport, Internet, "
                       "and Network Access. Each layer has specific responsibilities in data transmission.",
                content_type=ContentType.TEXT,
                hierarchical_context=["Chapter 3", "Network Protocols"],
                page_number=42,
                position_in_document=0.5,
                metadata={"topic": "networking", "difficulty": "intermediate"}
            ),
            ProcessedChunk(
                chunk_id="chunk_4",
                document_id="doc_2",
                content="The Shannon capacity formula C = B * log2(1 + SNR) defines the maximum "
                       "theoretical data rate for a communication channel with bandwidth B and signal-to-noise ratio SNR.",
                content_type=ContentType.FORMULA,
                hierarchical_context=["Chapter 4", "Information Theory"],
                page_number=67,
                position_in_document=0.7,
                metadata={"topic": "information_theory", "difficulty": "advanced"}
            ),
            ProcessedChunk(
                chunk_id="chunk_5",
                document_id="doc_3",
                content="Python implementation of BM25 algorithm:\n"
                       "def bm25_score(tf, df, N, k1=1.2, b=0.75):\n"
                       "    idf = math.log((N - df + 0.5) / (df + 0.5))\n"
                       "    return idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))",
                content_type=ContentType.CODE,
                hierarchical_context=["Appendix A", "Code Examples"],
                page_number=120,
                position_in_document=0.9,
                metadata={"topic": "algorithms", "difficulty": "advanced"}
            )
        ]
        
        # Set up the index
        self.retriever.setup_index(self.test_chunks)
    
    def test_text_preprocessing(self):
        """Test text preprocessing functionality."""
        # Test basic preprocessing
        text = "This is a TEST with PUNCTUATION!!! And numbers 123."
        tokens = self.retriever._preprocess_text(text)
        
        # Should be lowercase and filtered
        self.assertIn("test", tokens)
        self.assertNotIn("TEST", tokens)
        self.assertNotIn("!!!", tokens)
        
        # Technical terms should be preserved
        technical_text = "TCP/IP protocol uses HTTP and HTTPS protocols"
        tech_tokens = self.retriever._preprocess_text(technical_text)
        self.assertIn("tcp", tech_tokens)
        self.assertIn("http", tech_tokens)
        self.assertIn("https", tech_tokens)
    
    def test_technical_term_detection(self):
        """Test technical term detection."""
        # Test various technical patterns
        self.assertTrue(self.retriever._is_technical_term("TCP"))
        self.assertTrue(self.retriever._is_technical_term("HTTP"))
        self.assertTrue(self.retriever._is_technical_term("wifi"))
        self.assertTrue(self.retriever._is_technical_term("algorithm"))
        self.assertTrue(self.retriever._is_technical_term("test_function"))
        self.assertTrue(self.retriever._is_technical_term("192.168.1.1"))
        
        # Regular words should not be detected as technical
        self.assertFalse(self.retriever._is_technical_term("hello"))
        self.assertFalse(self.retriever._is_technical_term("world"))
        self.assertFalse(self.retriever._is_technical_term("the"))
    
    def test_inverted_index_building(self):
        """Test inverted index construction."""
        # Check that inverted index was built
        self.assertGreater(len(self.retriever.inverted_index), 0)
        
        # Check that specific terms are indexed
        self.assertIn("wireless", self.retriever.inverted_index)
        self.assertIn("communication", self.retriever.inverted_index)
        self.assertIn("tcp", self.retriever.inverted_index)
        
        # Check that chunk indices are correct
        wireless_chunks = self.retriever.inverted_index["wireless"]
        self.assertIn(0, wireless_chunks)  # First chunk contains "wireless"
    
    def test_bm25_index_setup(self):
        """Test BM25 index initialization."""
        # Check that BM25 index was created
        self.assertIsNotNone(self.retriever.bm25_index)
        self.assertEqual(len(self.retriever.chunks), 5)
    
    def test_keyword_search_basic(self):
        """Test basic keyword search functionality."""
        # Test search for wireless communication
        results = self.retriever.keyword_search("wireless communication", k=3)
        
        # Should return results
        self.assertGreater(len(results), 0)
        
        # Results should be RetrievalResult objects
        for result in results:
            self.assertIsInstance(result, RetrievalResult)
            self.assertEqual(result.retrieval_method, "keyword_bm25")
            self.assertGreater(result.score, 0)
        
        # Results should be sorted by score (descending)
        scores = [result.score for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_keyword_search_technical_terms(self):
        """Test keyword search with technical terms."""
        # Test search for TCP/IP
        results = self.retriever.keyword_search("TCP/IP protocol", k=5)
        
        # Should find the networking chunk
        self.assertGreater(len(results), 0)
        
        # Check that the correct chunk is highly ranked
        top_result = results[0]
        self.assertIn("TCP/IP", top_result.chunk.content)
    
    def test_keyword_search_formula_content(self):
        """Test keyword search in formula content."""
        # Test search for Shannon capacity
        results = self.retriever.keyword_search("Shannon capacity formula", k=5)
        
        # Should find the formula chunk
        self.assertGreater(len(results), 0)
        
        # Check metadata for matched terms
        for result in results:
            if "Shannon" in result.chunk.content:
                self.assertIn("matched_terms", result.metadata)
                break
    
    def test_keyword_search_code_content(self):
        """Test keyword search in code content."""
        # Test search for BM25 algorithm
        results = self.retriever.keyword_search("BM25 algorithm Python", k=5)
        
        # Should find the code chunk
        found_code = False
        for result in results:
            if result.chunk.content_type == ContentType.CODE:
                found_code = True
                self.assertIn("bm25", result.chunk.content.lower())
                break
        
        self.assertTrue(found_code, "Should find code chunk for BM25 algorithm")
    
    def test_retrieve_with_filters(self):
        """Test retrieval with metadata filters."""
        # Test filtering by content type
        filters = {"content_type": "text"}
        results = self.retriever.retrieve("communication", filters, k=5)
        
        # All results should be text content
        for result in results:
            self.assertEqual(result.chunk.content_type, ContentType.TEXT)
        
        # Test filtering by page number range
        filters = {"page_number": {"min": 10, "max": 50}}
        results = self.retriever.retrieve("protocol", filters, k=5)
        
        # All results should be within page range
        for result in results:
            self.assertGreaterEqual(result.chunk.page_number, 10)
            self.assertLessEqual(result.chunk.page_number, 50)
    
    def test_empty_query_handling(self):
        """Test handling of empty or invalid queries."""
        # Test empty query
        results = self.retriever.keyword_search("", k=5)
        self.assertEqual(len(results), 0)
        
        # Test query with only stopwords
        results = self.retriever.keyword_search("the and or", k=5)
        self.assertEqual(len(results), 0)
        
        # Test query with only punctuation
        results = self.retriever.keyword_search("!!! ??? ...", k=5)
        self.assertEqual(len(results), 0)
    
    def test_term_frequency(self):
        """Test term frequency calculation."""
        # Test frequency of common terms
        freq = self.retriever.get_term_frequency("communication")
        self.assertGreater(freq, 0)
        
        # Test frequency of non-existent term
        freq = self.retriever.get_term_frequency("nonexistentterm")
        self.assertEqual(freq, 0)
    
    def test_similar_terms(self):
        """Test similar terms functionality."""
        # Test getting similar terms
        similar = self.retriever.get_similar_terms("communication", max_results=3)
        self.assertIsInstance(similar, list)
        self.assertLessEqual(len(similar), 3)
        
        # Test with non-existent term
        similar = self.retriever.get_similar_terms("nonexistentterm", max_results=3)
        self.assertIsInstance(similar, list)
    
    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation."""
        # Test identical strings
        distance = self.retriever._levenshtein_distance("test", "test")
        self.assertEqual(distance, 0)
        
        # Test different strings
        distance = self.retriever._levenshtein_distance("test", "best")
        self.assertEqual(distance, 1)
        
        # Test empty strings
        distance = self.retriever._levenshtein_distance("", "test")
        self.assertEqual(distance, 4)
    
    def test_matched_terms_extraction(self):
        """Test extraction of matched terms between query and chunk."""
        query_tokens = ["wireless", "communication", "system"]
        matched = self.retriever._get_matched_terms(query_tokens, 0)
        
        # Should find matches in the first chunk
        self.assertIn("wireless", matched)
        self.assertIn("communication", matched)
    
    def test_multilingual_support(self):
        """Test basic multilingual support."""
        # Test French stopwords are filtered
        french_text = "Le système de communication sans fil utilise des ondes électromagnétiques"
        tokens = self.retriever._preprocess_text(french_text)
        
        # French stopwords should be filtered
        self.assertNotIn("le", tokens)
        self.assertNotIn("de", tokens)
        
        # Technical terms should be preserved
        self.assertIn("système", tokens)
        self.assertIn("communication", tokens)


if __name__ == "__main__":
    unittest.main()