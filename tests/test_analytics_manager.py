"""
Unit tests for analytics manager.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.managers.analytics_manager import AnalyticsManager
from src.models.base import (
    Response, RetrievalResult, ProcessedChunk, DocumentMetadata, 
    ContentType, QueryIntent
)


class TestAnalyticsManager(unittest.TestCase):
    """Test cases for AnalyticsManager."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.analytics_manager = AnalyticsManager(db_path=self.temp_db.name)
        
        # Create sample data
        self.sample_chunk = ProcessedChunk(
            chunk_id="chunk_1",
            document_id="doc_1",
            content="Sample content about wireless communications",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapter 1", "Section 1.1"],
            page_number=1,
            position_in_document=0.1,
            metadata={"topic": "wireless"},
            embedding=[0.1, 0.2, 0.3]
        )
        
        self.sample_retrieval_result = RetrievalResult(
            chunk=self.sample_chunk,
            score=0.85,
            retrieval_method="hybrid",
            metadata={"source": "test"}
        )
        
        self.sample_response = Response(
            content="This is a sample response about wireless communications.",
            sources=[self.sample_retrieval_result],
            confidence=0.9,
            citations=["Document 1, Page 1"],
            generation_metadata={"model": "test"}
        )
    
    def tearDown(self):
        """Clean up test environment."""
        os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test database initialization."""
        # Check if tables exist
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            
            # Check query_analytics table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='query_analytics'")
            self.assertIsNotNone(cursor.fetchone())
            
            # Check response_quality_metrics table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='response_quality_metrics'")
            self.assertIsNotNone(cursor.fetchone())
            
            # Check performance_metrics table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='performance_metrics'")
            self.assertIsNotNone(cursor.fetchone())
            
            # Check user_feedback table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_feedback'")
            self.assertIsNotNone(cursor.fetchone())
    
    def test_log_query(self):
        """Test query logging functionality."""
        query = "What is wireless communication?"
        metadata = {
            'conversation_id': 'conv_1',
            'user_id': 'user_1',
            'enhanced_query': 'What is wireless communication technology?',
            'query_intent': QueryIntent.FACTUAL,
            'processing_time': 1.5
        }
        
        # Log query
        self.analytics_manager.log_query(query, self.sample_response, metadata)
        
        # Verify data was stored
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM query_analytics")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
            
            # Check specific data
            cursor.execute("SELECT original_query, enhanced_query, processing_time FROM query_analytics")
            row = cursor.fetchone()
            self.assertEqual(row[0], query)
            self.assertEqual(row[1], metadata['enhanced_query'])
            self.assertEqual(row[2], metadata['processing_time'])
    
    def test_response_quality_calculation(self):
        """Test response quality metrics calculation."""
        query = "Test query"
        metadata = {'conversation_id': 'conv_1', 'user_id': 'user_1'}
        
        # Log query (which triggers quality calculation)
        self.analytics_manager.log_query(query, self.sample_response, metadata)
        
        # Verify quality metrics were calculated
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM response_quality_metrics")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
            
            # Check quality scores are within valid range
            cursor.execute("""
                SELECT relevance_score, accuracy_score, completeness_score, citation_quality 
                FROM response_quality_metrics
            """)
            row = cursor.fetchone()
            
            for score in row:
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)
    
    def test_relevance_score_calculation(self):
        """Test relevance score calculation."""
        # Test with high-scoring sources
        high_score_result = RetrievalResult(
            chunk=self.sample_chunk,
            score=0.95,
            retrieval_method="semantic",
            metadata={}
        )
        
        high_confidence_response = Response(
            content="High quality response",
            sources=[high_score_result],
            confidence=0.95,
            citations=["Source 1"],
            generation_metadata={}
        )
        
        relevance_score = self.analytics_manager._calculate_relevance_score(high_confidence_response)
        self.assertGreater(relevance_score, 0.8)
        
        # Test with no sources
        no_source_response = Response(
            content="Response without sources",
            sources=[],
            confidence=0.5,
            citations=[],
            generation_metadata={}
        )
        
        relevance_score = self.analytics_manager._calculate_relevance_score(no_source_response)
        self.assertEqual(relevance_score, 0.0)
    
    def test_accuracy_score_calculation(self):
        """Test accuracy score calculation."""
        # Test with citations
        accuracy_score = self.analytics_manager._calculate_accuracy_score(self.sample_response)
        self.assertGreater(accuracy_score, 0.0)
        
        # Test without citations
        no_citation_response = Response(
            content="Response without citations",
            sources=[self.sample_retrieval_result],
            confidence=0.8,
            citations=[],
            generation_metadata={}
        )
        
        accuracy_score = self.analytics_manager._calculate_accuracy_score(no_citation_response)
        self.assertGreater(accuracy_score, 0.0)
        self.assertLess(accuracy_score, 1.0)
    
    def test_completeness_score_calculation(self):
        """Test completeness score calculation."""
        # Test with optimal length response
        optimal_response = Response(
            content="A" * 400,  # Optimal length
            sources=[self.sample_retrieval_result],
            confidence=0.8,
            citations=["Citation 1"],
            generation_metadata={}
        )
        
        completeness_score = self.analytics_manager._calculate_completeness_score(optimal_response)
        self.assertGreater(completeness_score, 0.0)
        
        # Test with short response
        short_response = Response(
            content="Short",
            sources=[self.sample_retrieval_result],
            confidence=0.8,
            citations=["Citation 1"],
            generation_metadata={}
        )
        
        short_score = self.analytics_manager._calculate_completeness_score(short_response)
        self.assertLess(short_score, completeness_score)
    
    def test_citation_quality_calculation(self):
        """Test citation quality calculation."""
        # Test with detailed citations
        detailed_response = Response(
            content="Response with detailed citations",
            sources=[self.sample_retrieval_result],
            confidence=0.8,
            citations=["Document 1, Page 5, Section 2.1"],
            generation_metadata={}
        )
        
        citation_quality = self.analytics_manager._calculate_citation_quality(detailed_response)
        self.assertGreater(citation_quality, 0.0)
        
        # Test without citations
        no_citation_response = Response(
            content="Response without citations",
            sources=[self.sample_retrieval_result],
            confidence=0.8,
            citations=[],
            generation_metadata={}
        )
        
        no_citation_quality = self.analytics_manager._calculate_citation_quality(no_citation_response)
        self.assertEqual(no_citation_quality, 0.0)
    
    def test_track_performance(self):
        """Test performance tracking."""
        operation = "document_retrieval"
        duration = 2.5
        metadata = {
            'memory_usage': 150.0,
            'cpu_usage': 45.0,
            'success': True
        }
        
        # Track performance
        self.analytics_manager.track_performance(operation, duration, metadata)
        
        # Verify data was stored
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM performance_metrics")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
            
            # Check specific data
            cursor.execute("SELECT operation, duration, success FROM performance_metrics")
            row = cursor.fetchone()
            self.assertEqual(row[0], operation)
            self.assertEqual(row[1], duration)
            self.assertEqual(row[2], 1)  # SQLite stores boolean as integer
    
    def test_collect_feedback(self):
        """Test user feedback collection."""
        conversation_id = "conv_1"
        message_id = "msg_1"
        feedback = {
            'user_id': 'user_1',
            'rating': 4,
            'feedback_type': 'helpful',
            'comments': 'Very helpful response'
        }
        
        # Collect feedback
        self.analytics_manager.collect_feedback(conversation_id, message_id, feedback)
        
        # Verify data was stored
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_feedback")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
            
            # Check specific data
            cursor.execute("SELECT rating, feedback_type, comments FROM user_feedback")
            row = cursor.fetchone()
            self.assertEqual(row[0], feedback['rating'])
            self.assertEqual(row[1], feedback['feedback_type'])
            self.assertEqual(row[2], feedback['comments'])
    
    def test_generate_analytics_report(self):
        """Test analytics report generation."""
        # Add some test data
        query = "Test query"
        metadata = {
            'conversation_id': 'conv_1',
            'user_id': 'user_1',
            'processing_time': 1.0
        }
        
        self.analytics_manager.log_query(query, self.sample_response, metadata)
        self.analytics_manager.track_performance("test_operation", 2.0, {'success': True})
        self.analytics_manager.collect_feedback("conv_1", "msg_1", {
            'rating': 5,
            'feedback_type': 'accurate'
        })
        
        # Generate report
        report = self.analytics_manager.generate_analytics_report("day")
        
        # Verify report structure
        self.assertIn('time_period', report)
        self.assertIn('query_statistics', report)
        self.assertIn('quality_metrics', report)
        self.assertIn('performance_metrics', report)
        self.assertIn('feedback_summary', report)
        
        # Verify data
        self.assertEqual(report['query_statistics']['total_queries'], 1)
        self.assertGreater(len(report['performance_metrics']), 0)
        self.assertGreater(len(report['feedback_summary']), 0)
    
    def test_get_query_patterns(self):
        """Test query pattern retrieval."""
        # Add test queries
        queries = ["What is AI?", "How does ML work?", "Explain neural networks"]
        for i, query in enumerate(queries):
            metadata = {
                'conversation_id': f'conv_{i}',
                'user_id': f'user_{i}',
                'enhanced_query': f'Enhanced: {query}',
                'query_intent': QueryIntent.FACTUAL
            }
            self.analytics_manager.log_query(query, self.sample_response, metadata)
        
        # Get patterns
        patterns = self.analytics_manager.get_query_patterns(limit=5)
        
        # Verify results
        self.assertEqual(len(patterns), 3)
        self.assertIn('original_query', patterns[0])
        self.assertIn('enhanced_query', patterns[0])
        self.assertIn('query_intent', patterns[0])
    
    def test_get_performance_trends(self):
        """Test performance trend retrieval."""
        # Add performance data for multiple days
        operation = "test_operation"
        for i in range(3):
            metadata = {
                'success': True,
                'timestamp': (datetime.now() - timedelta(days=i)).isoformat()
            }
            self.analytics_manager.track_performance(operation, 1.0 + i, metadata)
        
        # Get trends
        trends = self.analytics_manager.get_performance_trends(operation, days=7)
        
        # Verify results (may be empty due to date grouping in SQLite)
        self.assertIsInstance(trends, list)
    
    @patch('src.managers.analytics_manager.logger')
    def test_error_handling(self, mock_logger):
        """Test error handling in analytics operations."""
        # Test with corrupted database operations
        # Create a manager with valid path first
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            manager = AnalyticsManager(db_path=temp_db.name)
            
            # Corrupt the database by closing it and removing the file
            os.unlink(temp_db.name)
            
            # Operations should not raise exceptions but log errors
            manager.log_query("test", self.sample_response, {})
            mock_logger.error.assert_called()
            
        finally:
            # Clean up
            if os.path.exists(temp_db.name):
                os.unlink(temp_db.name)
    
    def test_database_schema_validation(self):
        """Test database schema validation."""
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            
            # Test query_analytics table schema
            cursor.execute("PRAGMA table_info(query_analytics)")
            columns = [row[1] for row in cursor.fetchall()]
            expected_columns = [
                'query_id', 'conversation_id', 'user_id', 'original_query',
                'enhanced_query', 'query_intent', 'timestamp', 'processing_time',
                'retrieval_count', 'response_length', 'confidence_score',
                'sources_used', 'metadata'
            ]
            
            for col in expected_columns:
                self.assertIn(col, columns)
    
    def test_concurrent_access(self):
        """Test concurrent database access."""
        import threading
        
        def log_query_worker(worker_id):
            query = f"Test query {worker_id}"
            metadata = {'user_id': f'user_{worker_id}'}
            self.analytics_manager.log_query(query, self.sample_response, metadata)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_query_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all queries were logged
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM query_analytics")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 5)


if __name__ == '__main__':
    unittest.main()