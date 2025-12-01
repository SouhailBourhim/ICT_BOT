"""
Unit tests for result fusion and re-ranking system.
"""
import unittest
from datetime import datetime

from models.base import ProcessedChunk, ContentType, RetrievalResult
from retrievers.reranker import HybridReRanker


class TestHybridReRanker(unittest.TestCase):
    """Test cases for HybridReRanker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.reranker = HybridReRanker()
        
        # Create test chunks with different characteristics
        self.chunks = [
            ProcessedChunk(
                chunk_id="chunk_1",
                document_id="doc_1",
                content="Wireless communication systems overview and introduction",
                content_type=ContentType.TEXT,
                hierarchical_context=["Chapter 1", "Introduction", "Overview"],
                page_number=1,
                position_in_document=0.05,
                metadata={"topic": "wireless_communication", "difficulty": "basic"}
            ),
            ProcessedChunk(
                chunk_id="chunk_2",
                document_id="doc_1",
                content="The Shannon capacity formula: C = B * log2(1 + SNR)",
                content_type=ContentType.FORMULA,
                hierarchical_context=["Chapter 4", "Information Theory", "Capacity"],
                page_number=67,
                position_in_document=0.7,
                metadata={"topic": "information_theory", "difficulty": "advanced"}
            ),
            ProcessedChunk(
                chunk_id="chunk_3",
                document_id="doc_2",
                content="TCP/IP protocol implementation details",
                content_type=ContentType.TEXT,
                hierarchical_context=["Chapter 3", "Network Protocols", "TCP/IP"],
                page_number=42,
                position_in_document=0.5,
                metadata={"topic": "networking", "difficulty": "intermediate"}
            ),
            ProcessedChunk(
                chunk_id="chunk_4",
                document_id="doc_2",
                content="def calculate_bm25_score(tf, df, N):\n    return math.log(N/df) * tf",
                content_type=ContentType.CODE,
                hierarchical_context=["Appendix A", "Code Examples"],
                page_number=120,
                position_in_document=0.95,
                metadata={"topic": "algorithms", "difficulty": "advanced"}
            ),
            ProcessedChunk(
                chunk_id="chunk_5",
                document_id="doc_3",
                content="Rayleigh fading channel characteristics",
                content_type=ContentType.TEXT,
                hierarchical_context=["Chapter 2", "Fading Channels"],
                page_number=25,
                position_in_document=0.3,
                metadata={"topic": "fading", "difficulty": "intermediate"}
            )
        ]
        
        # Create test results for semantic search
        self.semantic_results = [
            RetrievalResult(
                chunk=self.chunks[0],
                score=0.95,
                retrieval_method="semantic",
                metadata={"embedding_similarity": 0.95}
            ),
            RetrievalResult(
                chunk=self.chunks[2],
                score=0.85,
                retrieval_method="semantic",
                metadata={"embedding_similarity": 0.85}
            ),
            RetrievalResult(
                chunk=self.chunks[4],
                score=0.75,
                retrieval_method="semantic",
                metadata={"embedding_similarity": 0.75}
            )
        ]
        
        # Create test results for keyword search
        self.keyword_results = [
            RetrievalResult(
                chunk=self.chunks[2],
                score=2.5,
                retrieval_method="keyword_bm25",
                metadata={"bm25_score": 2.5}
            ),
            RetrievalResult(
                chunk=self.chunks[1],
                score=2.2,
                retrieval_method="keyword_bm25",
                metadata={"bm25_score": 2.2}
            ),
            RetrievalResult(
                chunk=self.chunks[3],
                score=1.8,
                retrieval_method="keyword_bm25",
                metadata={"bm25_score": 1.8}
            )
        ]
    
    def test_rrf_initialization(self):
        """Test RRF re-ranker initialization."""
        # Test default initialization
        reranker = HybridReRanker()
        self.assertEqual(reranker.rrf_k, 60)
        self.assertEqual(reranker.semantic_weight, 0.6)
        self.assertEqual(reranker.keyword_weight, 0.4)
        
        # Test custom initialization
        reranker = HybridReRanker(rrf_k=30, semantic_weight=0.7, keyword_weight=0.3)
        self.assertEqual(reranker.rrf_k, 30)
        self.assertEqual(reranker.semantic_weight, 0.7)
        self.assertEqual(reranker.keyword_weight, 0.3)
    
    def test_weight_normalization(self):
        """Test that weights are normalized to sum to 1."""
        reranker = HybridReRanker(semantic_weight=0.8, keyword_weight=0.6)
        # Should be normalized to 0.8/1.4 and 0.6/1.4
        self.assertAlmostEqual(reranker.semantic_weight + reranker.keyword_weight, 1.0, places=5)
    
    def test_rrf_fusion_basic(self):
        """Test basic RRF fusion functionality."""
        fused_results = self.reranker.fuse_results_rrf(self.semantic_results, self.keyword_results)
        
        # Should have unique results (no duplicates)
        chunk_ids = [result.chunk.chunk_id for result in fused_results]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))
        
        # Should include results from both methods
        self.assertGreater(len(fused_results), 0)
        
        # Results should be sorted by score (descending)
        scores = [result.score for result in fused_results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        
        # All results should have hybrid_rrf method
        for result in fused_results:
            self.assertEqual(result.retrieval_method, "hybrid_rrf")
    
    def test_rrf_metadata_preservation(self):
        """Test that RRF preserves original scores and ranks in metadata."""
        fused_results = self.reranker.fuse_results_rrf(self.semantic_results, self.keyword_results)
        
        for result in fused_results:
            metadata = result.metadata
            
            # Should have RRF-specific metadata
            self.assertIn("rrf_score", metadata)
            self.assertIn("rrf_k", metadata)
            self.assertIn("semantic_weight", metadata)
            self.assertIn("keyword_weight", metadata)
            
            # Should have original scores if available
            chunk_id = result.chunk.chunk_id
            
            # Check if chunk was in semantic results
            semantic_found = any(r.chunk.chunk_id == chunk_id for r in self.semantic_results)
            if semantic_found:
                self.assertIsNotNone(metadata.get("semantic_score"))
                self.assertIsNotNone(metadata.get("semantic_rank"))
            
            # Check if chunk was in keyword results
            keyword_found = any(r.chunk.chunk_id == chunk_id for r in self.keyword_results)
            if keyword_found:
                self.assertIsNotNone(metadata.get("keyword_score"))
                self.assertIsNotNone(metadata.get("keyword_rank"))
    
    def test_rrf_score_calculation(self):
        """Test RRF score calculation logic."""
        # Test with simple case: one result in each method
        semantic_simple = [self.semantic_results[0]]  # rank 1
        keyword_simple = [self.keyword_results[0]]    # rank 1, different chunk
        
        fused = self.reranker.fuse_results_rrf(semantic_simple, keyword_simple)
        
        # Should have 2 results
        self.assertEqual(len(fused), 2)
        
        # Calculate expected RRF scores
        expected_semantic_only = 0.6 / (60 + 1)  # semantic_weight / (rrf_k + rank)
        expected_keyword_only = 0.4 / (60 + 1)   # keyword_weight / (rrf_k + rank)
        
        # Find results and check scores
        for result in fused:
            if result.chunk.chunk_id == semantic_simple[0].chunk.chunk_id:
                self.assertAlmostEqual(result.score, expected_semantic_only, places=5)
            elif result.chunk.chunk_id == keyword_simple[0].chunk.chunk_id:
                self.assertAlmostEqual(result.score, expected_keyword_only, places=5)
    
    def test_metadata_boost_calculation(self):
        """Test metadata-based boost calculation."""
        query = "wireless communication systems"
        
        # Test topic matching boost
        boost = self.reranker._calculate_metadata_boost(query, self.chunks[0])
        self.assertGreater(boost, 1.0)  # Should get boost for topic match
        
        # Test no topic match
        boost = self.reranker._calculate_metadata_boost("unrelated query", self.chunks[0])
        self.assertEqual(boost, 1.0)  # No boost for unrelated query
        
        # Test difficulty level boost
        technical_query = "algorithm implementation"
        boost = self.reranker._calculate_metadata_boost(technical_query, self.chunks[3])
        self.assertGreater(boost, 1.0)  # Advanced content should get boost for technical query
    
    def test_content_type_boost_calculation(self):
        """Test content type boost calculation."""
        # Test formula boost for mathematical query
        math_query = "Shannon capacity formula"
        boost = self.reranker._calculate_content_type_boost(math_query, self.chunks[1])
        self.assertGreater(boost, 1.0)
        
        # Test code boost for implementation query
        code_query = "implement BM25 algorithm"
        boost = self.reranker._calculate_content_type_boost(code_query, self.chunks[3])
        self.assertGreater(boost, 1.0)
        
        # Test penalty for mismatched content type
        boost = self.reranker._calculate_content_type_boost("general text query", self.chunks[1])
        self.assertLess(boost, 1.0)  # Formula content should get penalty for non-math query
    
    def test_position_boost_calculation(self):
        """Test position-based boost calculation."""
        # Test early position boost
        early_chunk = self.chunks[0]  # position 0.05
        boost = self.reranker._calculate_position_boost(early_chunk)
        self.assertGreater(boost, 1.0)
        
        # Test late position penalty
        late_chunk = self.chunks[3]  # position 0.95
        boost = self.reranker._calculate_position_boost(late_chunk)
        self.assertLess(boost, 1.0)
        
        # Test middle position (neutral)
        middle_chunk = self.chunks[2]  # position 0.5
        boost = self.reranker._calculate_position_boost(middle_chunk)
        self.assertEqual(boost, 1.0)
    
    def test_context_boost_calculation(self):
        """Test hierarchical context boost calculation."""
        query = "TCP/IP protocol"
        
        # Test context match boost
        boost = self.reranker._calculate_context_boost(query, self.chunks[2])
        self.assertGreater(boost, 1.0)  # Should get boost for "TCP/IP" in context
        
        # Test no context match
        boost = self.reranker._calculate_context_boost("unrelated query", self.chunks[2])
        self.assertEqual(boost, 1.0)
        
        # Test boost capping
        multi_match_query = "Chapter Network Protocols TCP/IP"
        boost = self.reranker._calculate_context_boost(multi_match_query, self.chunks[2])
        self.assertLessEqual(boost, 1.5)  # Should be capped at 1.5
    
    def test_technical_query_detection(self):
        """Test technical query detection."""
        # Test technical queries
        self.assertTrue(self.reranker._is_technical_query("TCP/IP protocol implementation"))
        self.assertTrue(self.reranker._is_technical_query("Shannon capacity algorithm"))
        self.assertTrue(self.reranker._is_technical_query("BM25 function"))
        
        # Test non-technical queries
        self.assertFalse(self.reranker._is_technical_query("hello world"))
        self.assertFalse(self.reranker._is_technical_query("general information"))
    
    def test_relevance_score_calculation(self):
        """Test enhanced relevance score calculation."""
        query = "wireless communication"
        result = self.semantic_results[0]  # Wireless communication chunk
        
        enhanced_score = self.reranker.calculate_relevance_score(query, result)
        
        # Enhanced score should be different from original
        self.assertNotEqual(enhanced_score, result.score)
        
        # Should be positive
        self.assertGreater(enhanced_score, 0)
    
    def test_rerank_functionality(self):
        """Test complete re-ranking functionality."""
        query = "wireless communication systems"
        results = self.semantic_results.copy()
        
        reranked = self.reranker.rerank(query, results)
        
        # Should have same number of results
        self.assertEqual(len(reranked), len(results))
        
        # Should have enhanced metadata
        for result in reranked:
            self.assertIn("original_score", result.metadata)
            self.assertIn("enhanced_score", result.metadata)
            self.assertIn("boost_applied", result.metadata)
            self.assertTrue(result.retrieval_method.endswith("_reranked"))
    
    def test_diversity_score_calculation(self):
        """Test diversity score calculation."""
        # Test with diverse results
        diverse_results = [
            self.semantic_results[0],  # Text, doc_1, wireless_communication, basic
            RetrievalResult(self.chunks[1], 0.8, "test", {}),  # Formula, doc_1, information_theory, advanced
            RetrievalResult(self.chunks[2], 0.7, "test", {}),  # Text, doc_2, networking, intermediate
            RetrievalResult(self.chunks[3], 0.6, "test", {})   # Code, doc_2, algorithms, advanced
        ]
        
        diversity_score = self.reranker.calculate_diversity_score(diverse_results)
        self.assertGreater(diversity_score, 0.5)  # Should be reasonably diverse
        
        # Test with identical results
        identical_results = [self.semantic_results[0]] * 3
        diversity_score = self.reranker.calculate_diversity_score(identical_results)
        self.assertLess(diversity_score, 0.5)  # Should have low diversity
        
        # Test with single result
        single_result = [self.semantic_results[0]]
        diversity_score = self.reranker.calculate_diversity_score(single_result)
        self.assertEqual(diversity_score, 1.0)  # Single result is perfectly diverse
    
    def test_diversify_results(self):
        """Test result diversification."""
        # Create results with some redundancy
        redundant_results = [
            RetrievalResult(self.chunks[0], 1.0, "test", {}),  # Text, doc_1
            RetrievalResult(self.chunks[2], 0.9, "test", {}),  # Text, doc_2
            RetrievalResult(self.chunks[4], 0.8, "test", {}),  # Text, doc_3
            RetrievalResult(self.chunks[1], 0.7, "test", {}),  # Formula, doc_1
            RetrievalResult(self.chunks[3], 0.6, "test", {})   # Code, doc_2
        ]
        
        diversified = self.reranker.diversify_results(redundant_results, max_results=3)
        
        # Should return requested number of results
        self.assertEqual(len(diversified), 3)
        
        # Should include top result
        self.assertEqual(diversified[0].chunk.chunk_id, redundant_results[0].chunk.chunk_id)
        
        # Should have better diversity than just taking top 3
        top_3_diversity = self.reranker.calculate_diversity_score(redundant_results[:3])
        diversified_diversity = self.reranker.calculate_diversity_score(diversified)
        self.assertGreaterEqual(diversified_diversity, top_3_diversity)
    
    def test_empty_results_handling(self):
        """Test handling of empty result lists."""
        # Test RRF with empty lists
        fused = self.reranker.fuse_results_rrf([], [])
        self.assertEqual(len(fused), 0)
        
        fused = self.reranker.fuse_results_rrf(self.semantic_results, [])
        self.assertEqual(len(fused), len(self.semantic_results))
        
        # Test reranking with empty list
        reranked = self.reranker.rerank("test query", [])
        self.assertEqual(len(reranked), 0)
        
        # Test diversification with empty list
        diversified = self.reranker.diversify_results([])
        self.assertEqual(len(diversified), 0)


if __name__ == "__main__":
    unittest.main()