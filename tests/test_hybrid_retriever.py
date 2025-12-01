"""
Integration tests for hybrid retrieval system.
"""
import unittest
import tempfile
import shutil
import os
import sqlite3
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.models.base import ProcessedChunk, ContentType, RetrievalResult
from src.retrievers.hybrid_retriever import HybridRetriever, SemanticRetriever


class TestSemanticRetriever(unittest.TestCase):
    """Test cases for SemanticRetriever."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.chroma_path = os.path.join(self.temp_dir, "test_chroma")
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.retrievers.hybrid_retriever.Chroma')
    @patch('src.retrievers.hybrid_retriever.OllamaEmbeddings')
    def test_semantic_retriever_initialization(self, mock_embeddings, mock_chroma):
        """Test semantic retriever initialization."""
        # Mock ChromaDB not existing
        retriever = SemanticRetriever(self.chroma_path)
        self.assertIsNone(retriever.db)
        
        # Mock ChromaDB existing
        os.makedirs(self.chroma_path)
        retriever = SemanticRetriever(self.chroma_path)
        mock_chroma.assert_called_once()
    
    def test_langchain_doc_to_chunk_conversion(self):
        """Test conversion from LangChain document to ProcessedChunk."""
        retriever = SemanticRetriever(self.chroma_path)
        
        # Mock LangChain document
        mock_doc = Mock()
        mock_doc.page_content = "Test content for wireless communication"
        mock_doc.metadata = {
            'chunk_id': 'test_chunk_1',
            'document_id': 'test_doc_1',
            'content_type': 'text',
            'hierarchical_context': '["Chapter 1", "Introduction"]',
            'page_number': 5,
            'position_in_document': 0.2
        }
        
        chunk = retriever._langchain_doc_to_chunk(mock_doc)
        
        self.assertEqual(chunk.chunk_id, 'test_chunk_1')
        self.assertEqual(chunk.document_id, 'test_doc_1')
        self.assertEqual(chunk.content, "Test content for wireless communication")
        self.assertEqual(chunk.content_type, ContentType.TEXT)
        self.assertEqual(chunk.hierarchical_context, ["Chapter 1", "Introduction"])
        self.assertEqual(chunk.page_number, 5)
        self.assertEqual(chunk.position_in_document, 0.2)
    
    def test_chroma_filter_building(self):
        """Test ChromaDB filter building from our filter format."""
        retriever = SemanticRetriever(self.chroma_path)
        
        # Test empty filters
        chroma_filter = retriever._build_chroma_filter({})
        self.assertIsNone(chroma_filter)
        
        # Test content type filter
        filters = {"content_type": "text"}
        chroma_filter = retriever._build_chroma_filter(filters)
        self.assertEqual(chroma_filter["content_type"], {"$eq": "text"})
        
        # Test page number range filter
        filters = {"page_number": {"min": 10, "max": 20}}
        chroma_filter = retriever._build_chroma_filter(filters)
        expected = {"$gte": 10, "$lte": 20}
        self.assertEqual(chroma_filter["page_number"], expected)
        
        # Test document ID filter
        filters = {"document_id": "doc_123"}
        chroma_filter = retriever._build_chroma_filter(filters)
        self.assertEqual(chroma_filter["document_id"], {"$eq": "doc_123"})


class TestHybridRetriever(unittest.TestCase):
    """Test cases for HybridRetriever."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.chroma_path = os.path.join(self.temp_dir, "test_chroma")
        self.metadata_db_path = os.path.join(self.temp_dir, "test_metadata.db")
        
        # Create test metadata database
        self._create_test_metadata_db()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_metadata_db(self):
        """Create test metadata database with sample data."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE documents (
                document_id TEXT PRIMARY KEY,
                title TEXT,
                course_module TEXT,
                document_type TEXT,
                creation_date TEXT,
                page_count INTEGER,
                language TEXT,
                topics TEXT,
                difficulty_level TEXT,
                file_path TEXT,
                file_size INTEGER,
                ingestion_date TEXT,
                chunk_count INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT,
                content TEXT,
                content_type TEXT,
                hierarchical_context TEXT,
                page_number INTEGER,
                position_in_document REAL,
                metadata TEXT
            )
        """)
        
        # Insert test data
        test_chunks = [
            (
                "chunk_1", "doc_1", 
                "Wireless communication systems use electromagnetic waves",
                "text", '["Chapter 1", "Introduction"]', 1, 0.1, '{}'
            ),
            (
                "chunk_2", "doc_1",
                "TCP/IP protocol stack implementation details",
                "text", '["Chapter 3", "Protocols"]', 25, 0.4, '{}'
            ),
            (
                "chunk_3", "doc_2",
                "Shannon capacity formula: C = B * log2(1 + SNR)",
                "formula", '["Chapter 4", "Information Theory"]', 67, 0.7, '{}'
            ),
            (
                "chunk_4", "doc_2",
                "def calculate_bm25_score(tf, df, N):\\n    return math.log(N/df) * tf",
                "code", '["Appendix A", "Code Examples"]', 120, 0.9, '{}'
            )
        ]
        
        cursor.executemany("""
            INSERT INTO chunks 
            (chunk_id, document_id, content, content_type, hierarchical_context,
             page_number, position_in_document, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, test_chunks)
        
        conn.commit()
        conn.close()
    
    @patch('src.retrievers.hybrid_retriever.SemanticRetriever')
    @patch('src.retrievers.hybrid_retriever.BM25Retriever')
    def test_hybrid_retriever_initialization(self, mock_bm25, mock_semantic):
        """Test hybrid retriever initialization."""
        retriever = HybridRetriever(
            chroma_path=self.chroma_path,
            metadata_db_path=self.metadata_db_path
        )
        
        # Check that components were initialized
        mock_semantic.assert_called_once()
        mock_bm25.assert_called_once()
        self.assertIsNotNone(retriever.reranker)
    
    def test_load_chunks_from_metadata_db(self):
        """Test loading chunks from metadata database."""
        retriever = HybridRetriever(
            chroma_path=self.chroma_path,
            metadata_db_path=self.metadata_db_path
        )
        
        chunks = retriever._load_chunks_from_metadata_db()
        
        # Should load 4 test chunks
        self.assertEqual(len(chunks), 4)
        
        # Check first chunk
        chunk = chunks[0]
        self.assertEqual(chunk.chunk_id, "chunk_1")
        self.assertEqual(chunk.document_id, "doc_1")
        self.assertIn("Wireless communication", chunk.content)
        self.assertEqual(chunk.content_type, ContentType.TEXT)
        self.assertEqual(chunk.hierarchical_context, ["Chapter 1", "Introduction"])
    
    def test_search_strategy_determination(self):
        """Test search strategy determination based on query characteristics."""
        retriever = HybridRetriever(
            chroma_path=self.chroma_path,
            metadata_db_path=self.metadata_db_path
        )
        
        # Test keyword-only strategy
        strategy = retriever._determine_search_strategy("TCP/IP")
        self.assertEqual(strategy, "keyword_only")
        
        strategy = retriever._determine_search_strategy("HTTP API")
        self.assertEqual(strategy, "keyword_only")
        
        # Test semantic-only strategy
        strategy = retriever._determine_search_strategy("explain wireless communication")
        self.assertEqual(strategy, "semantic_only")
        
        strategy = retriever._determine_search_strategy("what is the concept of fading")
        self.assertEqual(strategy, "semantic_only")
        
        # Test hybrid strategy
        strategy = retriever._determine_search_strategy("wireless communication protocols")
        self.assertEqual(strategy, "hybrid")
    
    @patch('src.retrievers.hybrid_retriever.SemanticRetriever')
    @patch('src.retrievers.hybrid_retriever.BM25Retriever')
    def test_hybrid_search_flow(self, mock_bm25_class, mock_semantic_class):
        """Test complete hybrid search flow."""
        # Mock retrievers
        mock_semantic = Mock()
        mock_bm25 = Mock()
        mock_semantic_class.return_value = mock_semantic
        mock_bm25_class.return_value = mock_bm25
        
        # Create test results
        semantic_results = [
            RetrievalResult(
                chunk=ProcessedChunk(
                    chunk_id="chunk_1", document_id="doc_1", content="Wireless test",
                    content_type=ContentType.TEXT, hierarchical_context=[],
                    page_number=1, position_in_document=0.1, metadata={}
                ),
                score=0.9, retrieval_method="semantic", metadata={}
            )
        ]
        
        keyword_results = [
            RetrievalResult(
                chunk=ProcessedChunk(
                    chunk_id="chunk_2", document_id="doc_1", content="Protocol test",
                    content_type=ContentType.TEXT, hierarchical_context=[],
                    page_number=2, position_in_document=0.2, metadata={}
                ),
                score=2.5, retrieval_method="keyword", metadata={}
            )
        ]
        
        mock_semantic.retrieve.return_value = semantic_results
        mock_bm25.retrieve.return_value = keyword_results
        
        # Initialize retriever
        retriever = HybridRetriever(
            chroma_path=self.chroma_path,
            metadata_db_path=self.metadata_db_path
        )
        
        # Test hybrid search
        results = retriever._perform_hybrid_search("test query", {}, k=5)
        
        # Should call both retrievers
        mock_semantic.retrieve.assert_called_once()
        mock_bm25.retrieve.assert_called_once()
        
        # Should return fused results
        self.assertIsInstance(results, list)
    
    def test_retrieval_stats(self):
        """Test retrieval system statistics."""
        retriever = HybridRetriever(
            chroma_path=self.chroma_path,
            metadata_db_path=self.metadata_db_path
        )
        
        stats = retriever.get_retrieval_stats()
        
        # Check structure
        self.assertIn("semantic_retriever", stats)
        self.assertIn("keyword_retriever", stats)
        self.assertIn("reranker", stats)
        self.assertIn("metadata_database", stats)
        
        # Check metadata database stats
        db_stats = stats["metadata_database"]
        self.assertEqual(db_stats["documents"], 0)  # No documents in test DB
        self.assertEqual(db_stats["chunks"], 4)     # 4 test chunks
    
    @patch('src.retrievers.hybrid_retriever.SemanticRetriever')
    @patch('src.retrievers.hybrid_retriever.BM25Retriever')
    def test_retrieve_with_filters(self, mock_bm25_class, mock_semantic_class):
        """Test retrieval with metadata filters."""
        # Mock retrievers
        mock_semantic = Mock()
        mock_bm25 = Mock()
        mock_semantic_class.return_value = mock_semantic
        mock_bm25_class.return_value = mock_bm25
        
        # Mock return empty results for simplicity
        mock_semantic.retrieve.return_value = []
        mock_bm25.retrieve.return_value = []
        
        retriever = HybridRetriever(
            chroma_path=self.chroma_path,
            metadata_db_path=self.metadata_db_path
        )
        
        # Test with filters
        filters = {"content_type": "text", "page_number": {"min": 1, "max": 50}}
        results = retriever.retrieve("test query", filters, k=5)
        
        # Should pass filters to both retrievers
        mock_semantic.retrieve.assert_called_with("test query", filters, 10)  # 2x k for fusion
        mock_bm25.retrieve.assert_called_with("test query", filters, 10)
    
    def test_nonexistent_metadata_db(self):
        """Test handling of non-existent metadata database."""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.db")
        
        retriever = HybridRetriever(
            chroma_path=self.chroma_path,
            metadata_db_path=nonexistent_path
        )
        
        chunks = retriever._load_chunks_from_metadata_db()
        self.assertEqual(len(chunks), 0)
    
    @patch('src.retrievers.hybrid_retriever.SemanticRetriever')
    @patch('src.retrievers.hybrid_retriever.BM25Retriever')
    def test_refresh_indexes(self, mock_bm25_class, mock_semantic_class):
        """Test index refresh functionality."""
        mock_semantic = Mock()
        mock_bm25 = Mock()
        mock_semantic_class.return_value = mock_semantic
        mock_bm25_class.return_value = mock_bm25
        
        retriever = HybridRetriever(
            chroma_path=self.chroma_path,
            metadata_db_path=self.metadata_db_path
        )
        
        # Test refresh
        retriever.refresh_indexes()
        
        # Should call initialization methods
        mock_semantic._initialize_db.assert_called()


class TestHybridRetrieverIntegration(unittest.TestCase):
    """Integration tests for hybrid retriever with real components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.chroma_path = os.path.join(self.temp_dir, "test_chroma")
        self.metadata_db_path = os.path.join(self.temp_dir, "test_metadata.db")
        
        # Create test chunks
        self.test_chunks = [
            ProcessedChunk(
                chunk_id="chunk_1",
                document_id="doc_1",
                content="Wireless communication systems use electromagnetic waves to transmit information",
                content_type=ContentType.TEXT,
                hierarchical_context=["Chapter 1", "Introduction"],
                page_number=1,
                position_in_document=0.1,
                metadata={"topic": "wireless"}
            ),
            ProcessedChunk(
                chunk_id="chunk_2",
                document_id="doc_1",
                content="TCP/IP protocol implementation with socket programming",
                content_type=ContentType.TEXT,
                hierarchical_context=["Chapter 3", "Protocols"],
                page_number=25,
                position_in_document=0.4,
                metadata={"topic": "networking"}
            ),
            ProcessedChunk(
                chunk_id="chunk_3",
                document_id="doc_2",
                content="The Shannon capacity formula defines maximum data rate",
                content_type=ContentType.FORMULA,
                hierarchical_context=["Chapter 4", "Information Theory"],
                page_number=67,
                position_in_document=0.7,
                metadata={"topic": "theory"}
            )
        ]
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_bm25_only_integration(self):
        """Test BM25-only retrieval integration."""
        # Create retriever with mocked semantic component
        with patch('src.retrievers.hybrid_retriever.SemanticRetriever') as mock_semantic_class:
            mock_semantic = Mock()
            mock_semantic.db = None  # Simulate ChromaDB not available
            mock_semantic_class.return_value = mock_semantic
            
            retriever = HybridRetriever(
                chroma_path=self.chroma_path,
                metadata_db_path=self.metadata_db_path
            )
            
            # Set up BM25 index manually
            retriever.keyword_retriever.setup_index(self.test_chunks)
            
            # Test keyword search
            results = retriever.keyword_retriever.keyword_search("TCP/IP protocol", k=3)
            
            # Should find relevant results
            self.assertGreater(len(results), 0)
            
            # Top result should be the TCP/IP chunk
            top_result = results[0]
            self.assertIn("TCP/IP", top_result.chunk.content)
    
    def test_result_fusion_integration(self):
        """Test result fusion with real reranker."""
        # Create mock results from both methods
        semantic_results = [
            RetrievalResult(
                chunk=self.test_chunks[0],
                score=0.9,
                retrieval_method="semantic",
                metadata={}
            ),
            RetrievalResult(
                chunk=self.test_chunks[2],
                score=0.7,
                retrieval_method="semantic",
                metadata={}
            )
        ]
        
        keyword_results = [
            RetrievalResult(
                chunk=self.test_chunks[1],
                score=2.5,
                retrieval_method="keyword",
                metadata={}
            ),
            RetrievalResult(
                chunk=self.test_chunks[0],  # Same chunk as semantic
                score=1.8,
                retrieval_method="keyword",
                metadata={}
            )
        ]
        
        # Create retriever and test fusion
        with patch('src.retrievers.hybrid_retriever.SemanticRetriever'):
            retriever = HybridRetriever(
                chroma_path=self.chroma_path,
                metadata_db_path=self.metadata_db_path
            )
            
            fused_results = retriever.fuse_results(semantic_results, keyword_results)
            
            # Should have unique results (no duplicates)
            chunk_ids = [r.chunk.chunk_id for r in fused_results]
            self.assertEqual(len(chunk_ids), len(set(chunk_ids)))
            
            # Should have RRF scores
            for result in fused_results:
                self.assertEqual(result.retrieval_method, "hybrid_rrf")
                self.assertIn("rrf_score", result.metadata)


if __name__ == "__main__":
    unittest.main()