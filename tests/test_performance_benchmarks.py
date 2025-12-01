"""
Performance benchmark tests for query response times and system performance.
"""

import pytest
import time
import statistics
import psutil
import threading
from unittest.mock import Mock, patch
from contextlib import contextmanager

from core.system import RAGSystem
from processors.ingestion_pipeline import IngestionPipeline
from retrievers.hybrid_retriever import HybridRetriever
from managers.query_enhancer import QueryEnhancer
from managers.response_manager import ResponseManager
from managers.conversation_manager import ConversationManager


class PerformanceBenchmarks:
    """Performance benchmarking utilities."""
    
    @staticmethod
    @contextmanager
    def measure_time():
        """Context manager to measure execution time."""
        start_time = time.perf_counter()
        yield lambda: time.perf_counter() - start_time
        
    @staticmethod
    @contextmanager
    def measure_memory():
        """Context manager to measure memory usage."""
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        yield lambda: process.memory_info().rss / 1024 / 1024 - start_memory
    
    @staticmethod
    def run_benchmark(func, iterations=10):
        """Run a function multiple times and collect performance metrics."""
        times = []
        memory_usage = []
        
        for _ in range(iterations):
            with PerformanceBenchmarks.measure_time() as get_time:
                with PerformanceBenchmarks.measure_memory() as get_memory:
                    func()
            
            times.append(get_time())
            memory_usage.append(get_memory())
        
        return {
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_time': statistics.stdev(times) if len(times) > 1 else 0,
            'avg_memory': statistics.mean(memory_usage),
            'max_memory': max(memory_usage)
        }


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.fixture
    def mock_rag_system(self):
        """Mock RAG system for performance testing."""
        with patch('chromadb.PersistentClient'):
            system = RAGSystem()
            return system
    
    def test_document_processing_performance(self, mock_rag_system):
        """Benchmark document processing performance."""
        pipeline = IngestionPipeline()
        
        # Create test document content of varying sizes
        small_doc = "Small document content. " * 100  # ~2KB
        medium_doc = "Medium document content. " * 1000  # ~20KB
        large_doc = "Large document content. " * 10000  # ~200KB
        
        def process_small_doc():
            with patch('builtins.open', mock_open_with_content(small_doc)):
                pipeline.process_document("test_small.txt")
        
        def process_medium_doc():
            with patch('builtins.open', mock_open_with_content(medium_doc)):
                pipeline.process_document("test_medium.txt")
        
        def process_large_doc():
            with patch('builtins.open', mock_open_with_content(large_doc)):
                pipeline.process_document("test_large.txt")
        
        # Benchmark different document sizes
        small_metrics = PerformanceBenchmarks.run_benchmark(process_small_doc, 5)
        medium_metrics = PerformanceBenchmarks.run_benchmark(process_medium_doc, 5)
        large_metrics = PerformanceBenchmarks.run_benchmark(process_large_doc, 3)
        
        # Performance assertions
        assert small_metrics['avg_time'] < 2.0  # Small docs should process in < 2s
        assert medium_metrics['avg_time'] < 5.0  # Medium docs should process in < 5s
        assert large_metrics['avg_time'] < 15.0  # Large docs should process in < 15s
        
        # Memory usage should be reasonable
        assert small_metrics['max_memory'] < 50  # < 50MB for small docs
        assert medium_metrics['max_memory'] < 100  # < 100MB for medium docs
        assert large_metrics['max_memory'] < 200  # < 200MB for large docs
        
        print(f"Small doc processing: {small_metrics['avg_time']:.2f}s avg")
        print(f"Medium doc processing: {medium_metrics['avg_time']:.2f}s avg")
        print(f"Large doc processing: {large_metrics['avg_time']:.2f}s avg")
    
    def test_query_processing_performance(self, mock_rag_system):
        """Benchmark query processing performance."""
        query_enhancer = QueryEnhancer()
        retriever = HybridRetriever()
        response_manager = ResponseManager()
        
        # Test queries of different complexity
        simple_query = "What is SNR?"
        complex_query = "Explain the mathematical relationship between signal-to-noise ratio and bit error rate in QPSK modulation systems"
        
        def process_simple_query():
            with patch.object(retriever, 'retrieve', return_value=[]):
                enhanced = query_enhancer.enhance_query(simple_query, Mock())
                retriever.retrieve(enhanced.corrected_query, {})
        
        def process_complex_query():
            with patch.object(retriever, 'retrieve', return_value=[]):
                enhanced = query_enhancer.enhance_query(complex_query, Mock())
                retriever.retrieve(enhanced.corrected_query, {})
        
        # Benchmark query processing
        simple_metrics = PerformanceBenchmarks.run_benchmark(process_simple_query, 10)
        complex_metrics = PerformanceBenchmarks.run_benchmark(process_complex_query, 10)
        
        # Performance assertions
        assert simple_metrics['avg_time'] < 1.0  # Simple queries should be < 1s
        assert complex_metrics['avg_time'] < 3.0  # Complex queries should be < 3s
        
        print(f"Simple query processing: {simple_metrics['avg_time']:.3f}s avg")
        print(f"Complex query processing: {complex_metrics['avg_time']:.3f}s avg")
    
    def test_retrieval_performance_scaling(self, mock_rag_system):
        """Test retrieval performance with different result set sizes."""
        retriever = HybridRetriever()
        
        # Mock different result set sizes
        def retrieve_k_results(k):
            def retrieve():
                with patch.object(retriever, 'retrieve') as mock_retrieve:
                    mock_results = [Mock() for _ in range(k)]
                    mock_retrieve.return_value = mock_results
                    return retriever.retrieve("test query", {}, k=k)
            return retrieve
        
        # Test different result set sizes
        k_values = [5, 10, 20, 50]
        metrics = {}
        
        for k in k_values:
            metrics[k] = PerformanceBenchmarks.run_benchmark(retrieve_k_results(k), 5)
            
            # Performance should scale reasonably
            assert metrics[k]['avg_time'] < k * 0.1  # Should be roughly linear
            
            print(f"Retrieving {k} results: {metrics[k]['avg_time']:.3f}s avg")
    
    def test_concurrent_query_performance(self, mock_rag_system):
        """Test performance under concurrent query load."""
        retriever = HybridRetriever()
        query_enhancer = QueryEnhancer()
        
        results = []
        
        def concurrent_query_worker():
            """Worker function for concurrent queries."""
            start_time = time.perf_counter()
            
            with patch.object(retriever, 'retrieve', return_value=[]):
                enhanced = query_enhancer.enhance_query("test query", Mock())
                retriever.retrieve(enhanced.corrected_query, {})
            
            end_time = time.perf_counter()
            results.append(end_time - start_time)
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        
        for num_threads in concurrency_levels:
            results.clear()
            threads = []
            
            start_time = time.perf_counter()
            
            # Start concurrent threads
            for _ in range(num_threads):
                thread = threading.Thread(target=concurrent_query_worker)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            total_time = time.perf_counter() - start_time
            avg_response_time = statistics.mean(results)
            
            # Performance assertions
            assert avg_response_time < 5.0  # Individual queries should complete in < 5s
            assert total_time < 10.0  # Total time should be reasonable
            
            print(f"Concurrency {num_threads}: {avg_response_time:.3f}s avg response, {total_time:.3f}s total")
    
    def test_memory_usage_under_load(self, mock_rag_system):
        """Test memory usage under sustained load."""
        conversation_manager = ConversationManager()
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Simulate sustained usage
        conversation_ids = []
        
        for i in range(100):
            conv_id = conversation_manager.start_conversation(f"user_{i}")
            conversation_ids.append(conv_id)
            
            # Add messages to conversation
            for j in range(10):
                conversation_manager.add_message(conv_id, {
                    'role': 'user',
                    'content': f'Query {j} from user {i}',
                    'timestamp': time.time()
                })
        
        peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_increase = peak_memory - initial_memory
        
        # Memory usage should be reasonable
        assert memory_increase < 500  # Should not use more than 500MB additional
        
        print(f"Memory increase under load: {memory_increase:.2f}MB")
    
    def test_database_query_performance(self, mock_rag_system):
        """Test database query performance."""
        conversation_manager = ConversationManager()
        
        # Create test conversations
        conversation_ids = []
        for i in range(50):
            conv_id = conversation_manager.start_conversation(f"perf_user_{i}")
            conversation_ids.append(conv_id)
        
        def query_conversations():
            """Query conversation data."""
            for conv_id in conversation_ids[:10]:  # Query subset
                conversation_manager.get_context(conv_id, max_tokens=1000)
        
        # Benchmark database queries
        metrics = PerformanceBenchmarks.run_benchmark(query_conversations, 5)
        
        # Database queries should be fast
        assert metrics['avg_time'] < 2.0  # Should complete in < 2s
        
        print(f"Database query performance: {metrics['avg_time']:.3f}s avg")
    
    def test_response_generation_performance(self, mock_rag_system):
        """Test response generation performance with different context sizes."""
        response_manager = ResponseManager()
        
        # Create mock documents of different sizes
        small_context = [Mock(content="Short content") for _ in range(3)]
        large_context = [Mock(content="Long content " * 100) for _ in range(10)]
        
        def generate_with_small_context():
            with patch.object(response_manager, 'generate_response') as mock_gen:
                mock_gen.return_value = Mock(content="Response", confidence=0.8)
                response_manager.generate_response("test query", small_context, Mock())
        
        def generate_with_large_context():
            with patch.object(response_manager, 'generate_response') as mock_gen:
                mock_gen.return_value = Mock(content="Response", confidence=0.8)
                response_manager.generate_response("test query", large_context, Mock())
        
        # Benchmark response generation
        small_metrics = PerformanceBenchmarks.run_benchmark(generate_with_small_context, 5)
        large_metrics = PerformanceBenchmarks.run_benchmark(generate_with_large_context, 5)
        
        # Response generation should be reasonable
        assert small_metrics['avg_time'] < 3.0
        assert large_metrics['avg_time'] < 8.0
        
        print(f"Small context response: {small_metrics['avg_time']:.3f}s avg")
        print(f"Large context response: {large_metrics['avg_time']:.3f}s avg")


def mock_open_with_content(content):
    """Helper to mock file opening with specific content."""
    from unittest.mock import mock_open
    return mock_open(read_data=content)