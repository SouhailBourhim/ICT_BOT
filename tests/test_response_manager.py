"""
Unit tests for ResponseManager.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List

from src.managers.response_manager import ResponseManager
from src.models.base import (
    Response, RetrievalResult, ProcessedChunk, DocumentMetadata, 
    ConversationContext, Message, ContentType
)


class TestResponseManager:
    """Test cases for ResponseManager."""
    
    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response."""
        mock_response = Mock()
        mock_response.content = "Voici la réponse avec citation [1] et [2]."
        return mock_response
    
    @pytest.fixture
    def sample_chunks(self):
        """Sample processed chunks for testing."""
        metadata1 = DocumentMetadata(
            document_id="doc1",
            title="Cours Réseaux",
            course_module="Réseaux",
            document_type="pdf",
            creation_date=datetime.now(),
            page_count=100,
            language="fr",
            topics=["TCP/IP", "Routage"],
            difficulty_level="intermediate",
            file_path="/path/to/doc1.pdf",
            file_size=1024000
        )
        
        chunk1 = ProcessedChunk(
            chunk_id="chunk1",
            document_id="doc1",
            content="Le protocole TCP garantit la fiabilité des transmissions.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 1", "Section 1.1"],
            page_number=15,
            position_in_document=0.15,
            metadata={"title": "Cours Réseaux"}
        )
        
        chunk2 = ProcessedChunk(
            chunk_id="chunk2",
            document_id="doc1",
            content="UDP est un protocole sans connexion plus rapide que TCP.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 1", "Section 1.2"],
            page_number=16,
            position_in_document=0.16,
            metadata={"title": "Cours Réseaux"}
        )
        
        return [chunk1, chunk2]
    
    @pytest.fixture
    def sample_retrieval_results(self, sample_chunks):
        """Sample retrieval results for testing."""
        return [
            RetrievalResult(
                chunk=sample_chunks[0],
                score=0.85,
                retrieval_method="semantic",
                metadata={"query_similarity": 0.85}
            ),
            RetrievalResult(
                chunk=sample_chunks[1],
                score=0.75,
                retrieval_method="hybrid",
                metadata={"query_similarity": 0.75}
            )
        ]
    
    @pytest.fixture
    def sample_conversation_context(self):
        """Sample conversation context for testing."""
        messages = [
            Message(
                message_id="msg1",
                role="user",
                content="Qu'est-ce que TCP?",
                timestamp=datetime.now(),
                sources=[],
                confidence=1.0
            ),
            Message(
                message_id="msg2",
                role="assistant",
                content="TCP est un protocole de transport fiable.",
                timestamp=datetime.now(),
                sources=["doc1"],
                confidence=0.9
            )
        ]
        
        return ConversationContext(
            conversation_id="conv1",
            recent_messages=messages,
            summary="Discussion sur les protocoles réseau",
            relevant_topics=["TCP", "protocoles"],
            context_tokens=150
        )
    
    @pytest.fixture
    def response_manager(self):
        """ResponseManager instance for testing."""
        with patch('src.managers.response_manager.ChatOllama'):
            with patch('src.managers.response_manager.get_settings') as mock_settings:
                mock_config = Mock()
                mock_config.model.ollama_model = "llama3"
                mock_settings.return_value = mock_config
                return ResponseManager()
    
    def test_init(self, response_manager):
        """Test ResponseManager initialization."""
        assert response_manager.llm_model == "llama3"
        assert response_manager.citation_prompt is not None
        assert response_manager.synthesis_prompt is not None
        assert response_manager.citation_pattern is not None
    
    def test_prepare_context_with_sources(self, response_manager, sample_retrieval_results):
        """Test context preparation with source numbering."""
        context = response_manager._prepare_context_with_sources(sample_retrieval_results)
        
        assert "[1] Source: Cours Réseaux - Page 15" in context
        assert "[2] Source: Cours Réseaux - Page 16" in context
        assert "Section: Chapitre 1 > Section 1.1" in context
        assert "Le protocole TCP garantit la fiabilité" in context
        assert "UDP est un protocole sans connexion" in context
    
    def test_format_conversation_context(self, response_manager, sample_conversation_context):
        """Test conversation context formatting."""
        context = response_manager._format_conversation_context(sample_conversation_context)
        
        assert "Étudiant: Qu'est-ce que TCP?" in context
        assert "Assistant: TCP est un protocole de transport fiable." in context
    
    def test_extract_citations(self, response_manager, sample_retrieval_results):
        """Test citation extraction from response."""
        response_content = "TCP est fiable [1] et UDP est rapide [2]. Voir aussi [1]."
        citations = response_manager._extract_citations(response_content, sample_retrieval_results)
        
        assert len(citations) == 2
        # Check that both citations are present (order may vary)
        citation_text = " ".join(citations)
        assert "[1] Cours Réseaux, page 15" in citation_text
        assert "[2] Cours Réseaux, page 16" in citation_text
        assert "section: Chapitre 1 > Section 1.1" in citation_text
    
    def test_extract_citations_invalid_numbers(self, response_manager, sample_retrieval_results):
        """Test citation extraction with invalid citation numbers."""
        response_content = "TCP est fiable [1] et UDP [5] est rapide [abc]."
        citations = response_manager._extract_citations(response_content, sample_retrieval_results)
        
        # Only valid citation [1] should be extracted
        assert len(citations) == 1
        assert "[1] Cours Réseaux, page 15" in citations[0]
    
    def test_format_citation(self, response_manager, sample_chunks):
        """Test individual citation formatting."""
        citation = response_manager._format_citation(sample_chunks[0], 1)
        
        expected = "[1] Cours Réseaux, page 15, section: Chapitre 1 > Section 1.1"
        assert citation == expected
    
    def test_calculate_confidence_high(self, response_manager, sample_retrieval_results):
        """Test confidence calculation for high-quality response."""
        response_content = "TCP garantit la fiabilité [1] tandis qu'UDP est plus rapide [2]."
        confidence = response_manager._calculate_confidence(response_content, sample_retrieval_results)
        
        # Should be high confidence (good sources, citations, length)
        assert confidence > 0.7
    
    def test_calculate_confidence_low(self, response_manager, sample_retrieval_results):
        """Test confidence calculation for low-quality response."""
        response_content = "Je ne sais pas exactement."
        confidence = response_manager._calculate_confidence(response_content, sample_retrieval_results)
        
        # Should be low confidence (uncertainty, short response, no citations)
        assert confidence < 0.5
    
    def test_calculate_confidence_no_sources(self, response_manager):
        """Test confidence calculation with no sources."""
        confidence = response_manager._calculate_confidence("Some response", [])
        assert confidence == 0.0
    
    def test_add_citations_existing(self, response_manager, sample_retrieval_results):
        """Test adding citations when they already exist."""
        response_with_citations = "TCP est fiable [1]."
        result = response_manager.add_citations(response_with_citations, sample_retrieval_results)
        
        # Should not modify response that already has citations
        assert result == response_with_citations
    
    def test_add_citations_missing(self, response_manager, sample_retrieval_results):
        """Test adding citations when they are missing."""
        response_without_citations = "TCP est fiable."
        result = response_manager.add_citations(response_without_citations, sample_retrieval_results)
        
        assert "Sources:" in result
        assert "[1] Cours Réseaux, page 15" in result
        assert "[2] Cours Réseaux, page 16" in result
    
    def test_group_sources_by_document(self, response_manager, sample_retrieval_results):
        """Test grouping sources by document."""
        groups = response_manager._group_sources_by_document(sample_retrieval_results)
        
        assert "doc1" in groups
        assert len(groups["doc1"]) == 2
    
    def test_prepare_sources_for_synthesis(self, response_manager, sample_retrieval_results):
        """Test preparing sources for synthesis."""
        groups = response_manager._group_sources_by_document(sample_retrieval_results)
        synthesis_content = response_manager._prepare_sources_for_synthesis(groups)
        
        assert "=== Cours Réseaux ===" in synthesis_content
        assert "Extrait 1 (Page 15" in synthesis_content
        assert "Extrait 2 (Page 16" in synthesis_content
        assert "Le protocole TCP garantit" in synthesis_content
        assert "UDP est un protocole" in synthesis_content
    
    @patch('src.managers.response_manager.ChatOllama')
    def test_generate_response_success(self, mock_ollama, sample_retrieval_results, 
                                     sample_conversation_context, mock_llm_response):
        """Test successful response generation."""
        # Setup mocks
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_llm_response
        mock_ollama.return_value = mock_llm
        
        with patch('src.managers.response_manager.get_settings') as mock_settings:
            mock_config = Mock()
            mock_config.model.ollama_model = "llama3"
            mock_settings.return_value = mock_config
            
            manager = ResponseManager()
            
            # Mock the chain creation
            with patch.object(manager, '_generate_llm_response', return_value=mock_llm_response.content):
                response = manager.generate_response(
                    "Qu'est-ce que TCP?",
                    sample_retrieval_results,
                    sample_conversation_context
                )
        
        assert isinstance(response, Response)
        assert response.content == mock_llm_response.content
        assert len(response.sources) == 2
        assert response.confidence > 0
        assert len(response.citations) == 2
        assert "timestamp" in response.generation_metadata
    
    def test_synthesize_sources_success(self, response_manager, sample_retrieval_results):
        """Test successful source synthesis using synthesis manager."""
        # Mock the synthesis manager
        with patch.object(response_manager.synthesis_manager, 'synthesize_sources') as mock_synthesize:
            from managers.synthesis_manager import SynthesisResult
            
            mock_result = SynthesisResult(
                synthesized_content="Synthèse test: TCP est fiable.",
                source_reliability=[],
                detected_conflicts=[],
                synthesis_confidence=0.8,
                methodology_notes="Test methodology"
            )
            mock_synthesize.return_value = mock_result
            
            synthesis = response_manager.synthesize_sources(sample_retrieval_results)
            
            assert "Synthèse test: TCP est fiable." in synthesis
            assert "Confiance de la synthèse: 0.80" in synthesis
        
        # Test empty sources handling
        empty_synthesis = response_manager.synthesize_sources([])
        assert empty_synthesis == ""
    
    def test_synthesize_sources_empty(self, response_manager):
        """Test source synthesis with empty sources."""
        synthesis = response_manager.synthesize_sources([])
        assert synthesis == ""
    
    @patch('src.managers.response_manager.ChatOllama')
    def test_generate_response_error_handling(self, mock_ollama, sample_retrieval_results):
        """Test error handling in response generation."""
        # Setup mock to raise exception
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM Error")
        mock_ollama.return_value = mock_llm
        
        with patch('src.managers.response_manager.get_settings') as mock_settings:
            mock_config = Mock()
            mock_config.model.ollama_model = "llama3"
            mock_settings.return_value = mock_config
            
            manager = ResponseManager()
            
            with pytest.raises(Exception):
                manager.generate_response("Test query", sample_retrieval_results)
    
    def test_assess_confidence(self, response_manager, sample_retrieval_results):
        """Test confidence assessment method."""
        response_content = "TCP est fiable [1] et UDP est rapide [2]."
        confidence = response_manager.assess_confidence(response_content, sample_retrieval_results)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably confident
    
    def test_citation_pattern_matching(self, response_manager):
        """Test citation pattern regex."""
        text = "Information [1] and more info [2] and invalid [abc] citation."
        matches = response_manager.citation_pattern.findall(text)
        
        assert matches == ['1', '2']
    
    def test_uncertainty_detection_in_confidence(self, response_manager, sample_retrieval_results):
        """Test that uncertainty phrases reduce confidence."""
        uncertain_response = "Je ne sais pas exactement, mais il semble que TCP soit fiable [1]."
        certain_response = "TCP est fiable [1]."
        
        uncertain_confidence = response_manager._calculate_confidence(uncertain_response, sample_retrieval_results)
        certain_confidence = response_manager._calculate_confidence(certain_response, sample_retrieval_results)
        
        assert uncertain_confidence < certain_confidence


if __name__ == "__main__":
    pytest.main([__file__])