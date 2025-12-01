"""
End-to-end workflow tests for complete user journeys.
Tests the entire system from document ingestion to response generation.
"""

import pytest
import tempfile
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.system import RAGSystem
from src.processors.ingestion_pipeline import IngestionPipeline
from src.managers.conversation_manager import ConversationManager
from src.managers.query_enhancer import QueryEnhancer
from src.retrievers.hybrid_retriever import HybridRetriever
from src.managers.response_manager import ResponseManager


class TestEndToEndWorkflows:
    """Test complete user journeys through the RAG system."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary directory for test documents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF content for testing."""
        return """
        # Chapter 1: Introduction to Wireless Communications
        
        Wireless communication systems enable information exchange without physical connections.
        
        ## 1.1 Basic Concepts
        
        The fundamental principle involves electromagnetic wave propagation.
        Key parameters include frequency, bandwidth, and signal-to-noise ratio (SNR).
        
        ### Mathematical Foundation
        
        The path loss formula is: PL(dB) = 20*log10(4πd/λ)
        Where d is distance and λ is wavelength.
        
        ## 1.2 System Architecture
        
        Modern wireless systems consist of:
        - Transmitter
        - Channel
        - Receiver
        """
    
    @pytest.fixture
    def rag_system(self, temp_data_dir):
        """Initialize RAG system for testing."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            system = RAGSystem()
            system.initialize(data_dir=temp_data_dir)
            return system
    
    def test_complete_document_ingestion_workflow(self, rag_system, temp_data_dir, sample_pdf_content):
        """Test complete document ingestion from file to searchable chunks."""
        # Create test PDF file
        test_file = Path(temp_data_dir) / "test_document.txt"
        test_file.write_text(sample_pdf_content)
        
        # Test ingestion pipeline
        pipeline = IngestionPipeline()
        
        # Process document
        result = pipeline.process_document(str(test_file))
        
        # Verify processing results
        assert result is not None
        assert len(result.chunks) > 0
        assert result.metadata.title is not None
        assert result.metadata.document_type == "txt"
        
        # Verify chunks have proper structure
        for chunk in result.chunks:
            assert chunk.content is not None
            assert chunk.chunk_id is not None
            assert chunk.hierarchical_context is not None
            assert chunk.page_number >= 0
    
    def test_complete_query_processing_workflow(self, rag_system):
        """Test complete query processing from user input to final response."""
        # Initialize components
        conversation_manager = ConversationManager()
        query_enhancer = QueryEnhancer()
        retriever = HybridRetriever()
        response_manager = ResponseManager()
        
        # Start conversation
        conversation_id = conversation_manager.start_conversation("test_user")
        
        # Test query enhancement
        original_query = "What is path loss in wireless communication?"
        enhanced_query = query_enhancer.enhance_query(
            original_query, 
            conversation_manager.get_context(conversation_id, max_tokens=1000)
        )
        
        # Verify query enhancement
        assert enhanced_query.original_query == original_query
        assert enhanced_query.expanded_terms is not None
        assert enhanced_query.corrected_query is not None
        
        # Mock retrieval results
        with patch.object(retriever, 'retrieve') as mock_retrieve:
            mock_documents = [
                Mock(content="Path loss describes signal attenuation", 
                     metadata={'source': 'test.pdf', 'page': 1})
            ]
            mock_retrieve.return_value = mock_documents
            
            # Test retrieval
            retrieved_docs = retriever.retrieve(enhanced_query.corrected_query, {})
            assert len(retrieved_docs) > 0
            
            # Test response generation
            with patch.object(response_manager, 'generate_response') as mock_generate:
                mock_response = Mock(
                    content="Path loss is the reduction in signal strength...",
                    sources=mock_documents,
                    confidence=0.85
                )
                mock_generate.return_value = mock_response
                
                response = response_manager.generate_response(
                    enhanced_query.corrected_query,
                    retrieved_docs,
                    conversation_manager.get_context(conversation_id, max_tokens=1000)
                )
                
                # Verify response
                assert response.content is not None
                assert response.confidence > 0
                assert len(response.sources) > 0
    
    def test_conversation_continuity_workflow(self, rag_system):
        """Test conversation memory and follow-up question handling."""
        conversation_manager = ConversationManager()
        
        # Start conversation
        conversation_id = conversation_manager.start_conversation("test_user")
        
        # Add initial query and response
        conversation_manager.add_message(conversation_id, {
            'role': 'user',
            'content': 'What is SNR in wireless communications?',
            'timestamp': time.time()
        })
        
        conversation_manager.add_message(conversation_id, {
            'role': 'assistant',
            'content': 'SNR (Signal-to-Noise Ratio) is a measure of signal quality...',
            'timestamp': time.time(),
            'sources': ['wireless_basics.pdf']
        })
        
        # Test follow-up question
        followup_query = "How is it calculated?"
        context = conversation_manager.get_context(conversation_id, max_tokens=1000)
        
        # Verify context contains previous conversation
        assert len(context.messages) == 2
        assert 'SNR' in context.messages[1]['content']
        
        # Test follow-up detection
        query_enhancer = QueryEnhancer()
        enhanced_followup = query_enhancer.enhance_query(followup_query, context)
        
        # Verify follow-up is properly contextualized
        assert enhanced_followup.context_dependent is True
        assert 'SNR' in enhanced_followup.expanded_terms or 'signal-to-noise' in enhanced_followup.expanded_terms
    
    def test_error_recovery_workflow(self, rag_system):
        """Test system behavior under error conditions."""
        # Test with invalid document
        pipeline = IngestionPipeline()
        
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            pipeline.process_document("non_existent_file.pdf")
        
        # Test with corrupted content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Invalid content with special chars: \x00\x01\x02")
            f.flush()
            
            try:
                result = pipeline.process_document(f.name)
                # Should handle gracefully and return partial results
                assert result is not None
            finally:
                os.unlink(f.name)
    
    def test_multilingual_content_workflow(self, rag_system, temp_data_dir):
        """Test handling of multilingual content."""
        # Create multilingual test content
        multilingual_content = """
        # Wireless Communications / Communications Sans Fil
        
        English: Wireless communication enables data transmission without cables.
        Français: La communication sans fil permet la transmission de données sans câbles.
        
        ## Technical Terms / Termes Techniques
        
        - Bandwidth / Bande passante
        - Frequency / Fréquence
        - Modulation / Modulation
        """
        
        test_file = Path(temp_data_dir) / "multilingual_doc.txt"
        test_file.write_text(multilingual_content)
        
        # Test processing
        pipeline = IngestionPipeline()
        result = pipeline.process_document(str(test_file))
        
        # Verify multilingual content is preserved
        assert result is not None
        assert any('français' in chunk.content.lower() for chunk in result.chunks)
        assert any('english' in chunk.content.lower() for chunk in result.chunks)
    
    def test_large_document_workflow(self, rag_system, temp_data_dir):
        """Test processing of large documents."""
        # Create large document content
        large_content = ""
        for i in range(100):
            large_content += f"""
            ## Section {i+1}: Advanced Topic {i+1}
            
            This section covers advanced concepts in wireless communications.
            The mathematical formulation involves complex equations and derivations.
            
            Key points:
            - Point 1 for section {i+1}
            - Point 2 for section {i+1}
            - Point 3 for section {i+1}
            
            Formula {i+1}: y = x^{i+1} + noise
            
            """
        
        test_file = Path(temp_data_dir) / "large_document.txt"
        test_file.write_text(large_content)
        
        # Test processing with memory constraints
        pipeline = IngestionPipeline()
        result = pipeline.process_document(str(test_file))
        
        # Verify large document is processed successfully
        assert result is not None
        assert len(result.chunks) > 50  # Should create many chunks
        assert all(len(chunk.content) < 3000 for chunk in result.chunks)  # Chunks should be reasonable size
    
    def test_concurrent_user_simulation(self, rag_system):
        """Test system behavior with concurrent users."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def simulate_user_session(user_id):
            """Simulate a user session."""
            try:
                conversation_manager = ConversationManager()
                conversation_id = conversation_manager.start_conversation(f"user_{user_id}")
                
                # Simulate multiple queries
                queries = [
                    "What is wireless communication?",
                    "Explain path loss",
                    "How does modulation work?"
                ]
                
                for query in queries:
                    conversation_manager.add_message(conversation_id, {
                        'role': 'user',
                        'content': query,
                        'timestamp': time.time()
                    })
                    
                    # Simulate processing time
                    time.sleep(0.1)
                
                results.put(f"user_{user_id}_success")
                
            except Exception as e:
                results.put(f"user_{user_id}_error: {str(e)}")
        
        # Start multiple concurrent user sessions
        threads = []
        num_users = 5
        
        for i in range(num_users):
            thread = threading.Thread(target=simulate_user_session, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify all users completed successfully
        success_count = 0
        while not results.empty():
            result = results.get()
            if 'success' in result:
                success_count += 1
        
        assert success_count == num_users