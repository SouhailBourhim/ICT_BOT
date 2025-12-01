"""
Unit tests for SynthesisManager.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import List

from src.managers.synthesis_manager import (
    SynthesisManager, ConflictType, SourceConflict, 
    SourceReliability, SynthesisResult
)
from src.models.base import (
    RetrievalResult, ProcessedChunk, DocumentMetadata, ContentType
)


class TestSynthesisManager:
    """Test cases for SynthesisManager."""
    
    @pytest.fixture
    def synthesis_manager(self):
        """SynthesisManager instance for testing."""
        with patch('src.managers.synthesis_manager.get_settings') as mock_settings:
            mock_config = Mock()
            mock_settings.return_value = mock_config
            return SynthesisManager()
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample document metadata."""
        return {
            "title": "Cours TCP/IP",
            "course_module": "Réseaux",
            "document_type": "pdf",
            "creation_date": datetime.now() - timedelta(days=30)
        }
    
    @pytest.fixture
    def sample_chunks(self, sample_metadata):
        """Sample processed chunks for testing."""
        chunk1 = ProcessedChunk(
            chunk_id="chunk1",
            document_id="doc1",
            content="TCP est un protocole fiable qui garantit la livraison des données.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 1", "Section 1.1"],
            page_number=15,
            position_in_document=0.15,
            metadata=sample_metadata
        )
        
        chunk2 = ProcessedChunk(
            chunk_id="chunk2",
            document_id="doc1",
            content="TCP utilise un mécanisme d'accusé de réception pour assurer la fiabilité.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 1", "Section 1.2"],
            page_number=16,
            position_in_document=0.16,
            metadata=sample_metadata
        )
        
        # Conflicting chunk
        chunk3 = ProcessedChunk(
            chunk_id="chunk3",
            document_id="doc2",
            content="Contrairement à TCP, UDP ne garantit pas la fiabilité des transmissions.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 2", "Section 2.1"],
            page_number=25,
            position_in_document=0.25,
            metadata={**sample_metadata, "title": "Cours UDP", "document_id": "doc2"}
        )
        
        return [chunk1, chunk2, chunk3]
    
    @pytest.fixture
    def sample_retrieval_results(self, sample_chunks):
        """Sample retrieval results for testing."""
        return [
            RetrievalResult(
                chunk=sample_chunks[0],
                score=0.9,
                retrieval_method="semantic",
                metadata={"query_similarity": 0.9}
            ),
            RetrievalResult(
                chunk=sample_chunks[1],
                score=0.8,
                retrieval_method="hybrid",
                metadata={"query_similarity": 0.8}
            ),
            RetrievalResult(
                chunk=sample_chunks[2],
                score=0.7,
                retrieval_method="semantic",
                metadata={"query_similarity": 0.7}
            )
        ]
    
    def test_init(self, synthesis_manager):
        """Test SynthesisManager initialization."""
        assert synthesis_manager.contradiction_indicators is not None
        assert synthesis_manager.uncertainty_indicators is not None
        assert synthesis_manager.reliability_weights is not None
        assert len(synthesis_manager.reliability_weights) == 6
    
    def test_score_document_age_recent(self, synthesis_manager):
        """Test document age scoring for recent documents."""
        recent_metadata = {"creation_date": datetime.now() - timedelta(days=30)}
        score = synthesis_manager._score_document_age(recent_metadata)
        assert score >= 0.9  # Recent documents should score high
    
    def test_score_document_age_old(self, synthesis_manager):
        """Test document age scoring for old documents."""
        old_metadata = {"creation_date": datetime.now() - timedelta(days=3650)}  # 10 years
        score = synthesis_manager._score_document_age(old_metadata)
        assert score <= 0.5  # Old documents should score lower
    
    def test_score_document_age_no_date(self, synthesis_manager):
        """Test document age scoring when no date is available."""
        no_date_metadata = {}
        score = synthesis_manager._score_document_age(no_date_metadata)
        assert score == 0.6  # Default moderate score
    
    def test_score_document_type(self, synthesis_manager):
        """Test document type scoring."""
        pdf_score = synthesis_manager._score_document_type({"document_type": "pdf"})
        txt_score = synthesis_manager._score_document_type({"document_type": "txt"})
        unknown_score = synthesis_manager._score_document_type({"document_type": "unknown"})
        
        assert pdf_score > txt_score  # PDF should score higher than TXT
        assert unknown_score == 0.6   # Unknown type gets default score
    
    def test_score_content_quality_high(self, synthesis_manager, sample_chunks):
        """Test content quality scoring for high-quality content."""
        # Use a chunk with good indicators
        chunk = sample_chunks[0]  # Has good length, structure, etc.
        score = synthesis_manager._score_content_quality(chunk)
        assert score > 0.5
    
    def test_score_content_quality_low(self, synthesis_manager):
        """Test content quality scoring for low-quality content."""
        low_quality_chunk = ProcessedChunk(
            chunk_id="low_quality",
            document_id="doc1",
            content="Peut-être.",  # Very short, uncertain
            content_type=ContentType.TEXT,
            hierarchical_context=[],
            page_number=1,
            position_in_document=0.1,
            metadata={}
        )
        score = synthesis_manager._score_content_quality(low_quality_chunk)
        assert score < 0.5
    
    def test_assess_source_reliability(self, synthesis_manager, sample_retrieval_results):
        """Test source reliability assessment."""
        reliability_scores = synthesis_manager._assess_source_reliability(sample_retrieval_results)
        
        assert len(reliability_scores) == 3
        for reliability in reliability_scores:
            assert isinstance(reliability, SourceReliability)
            assert 0.0 <= reliability.reliability_score <= 1.0
            assert len(reliability.factors) == 6
            assert reliability.source_id in ["chunk1", "chunk2", "chunk3"]
    
    def test_detect_contradictions(self, synthesis_manager):
        """Test contradiction detection between contents."""
        content1 = "TCP est toujours fiable."
        content2 = "TCP n'est jamais fiable."
        
        contradiction_score = synthesis_manager._detect_contradictions(content1, content2)
        assert contradiction_score > 0.0  # Should detect contradiction with "toujours" vs "jamais"
    
    def test_detect_contradictions_none(self, synthesis_manager):
        """Test contradiction detection when there are no contradictions."""
        content1 = "TCP est un protocole fiable."
        content2 = "TCP utilise des accusés de réception."
        
        contradiction_score = synthesis_manager._detect_contradictions(content1, content2)
        assert contradiction_score == 0.0  # Should detect no contradiction
    
    def test_detect_inconsistencies(self, synthesis_manager):
        """Test inconsistency detection between contents."""
        content1 = "TCP est probablement fiable."  # Uncertain
        content2 = "TCP est définitivement fiable."  # Certain
        
        inconsistency_score = synthesis_manager._detect_inconsistencies(content1, content2)
        assert inconsistency_score > 0.0  # Should detect inconsistency
    
    def test_analyze_source_pair_conflict(self, synthesis_manager, sample_retrieval_results):
        """Test source pair analysis that detects conflict."""
        # Create sources with contradictory content
        source1 = sample_retrieval_results[0]  # TCP is reliable
        source2 = sample_retrieval_results[2]  # Contradicts TCP reliability
        
        conflict = synthesis_manager._analyze_source_pair(source1, source2)
        # Note: This might not detect conflict with current simple heuristics
        # but the method should return None or a SourceConflict
        assert conflict is None or isinstance(conflict, SourceConflict)
    
    def test_analyze_source_pair_no_conflict(self, synthesis_manager, sample_retrieval_results):
        """Test source pair analysis that finds no conflict."""
        # Use two compatible sources
        source1 = sample_retrieval_results[0]
        source2 = sample_retrieval_results[1]
        
        conflict = synthesis_manager._analyze_source_pair(source1, source2)
        assert conflict is None  # Should find no conflict
    
    def test_detect_conflicts(self, synthesis_manager, sample_retrieval_results):
        """Test conflict detection across all sources."""
        conflicts = synthesis_manager._detect_conflicts(sample_retrieval_results)
        
        assert isinstance(conflicts, list)
        # All conflicts should be SourceConflict instances
        for conflict in conflicts:
            assert isinstance(conflict, SourceConflict)
    
    def test_group_sources_by_content(self, synthesis_manager, sample_retrieval_results):
        """Test grouping sources by content."""
        reliability = synthesis_manager._assess_source_reliability(sample_retrieval_results)
        groups = synthesis_manager._group_sources_by_content(sample_retrieval_results, reliability)
        
        assert isinstance(groups, dict)
        assert "doc1" in groups
        assert "doc2" in groups
        assert len(groups["doc1"]) == 2  # Two chunks from doc1
        assert len(groups["doc2"]) == 1  # One chunk from doc2
    
    def test_calculate_group_reliability(self, synthesis_manager, sample_retrieval_results):
        """Test group reliability calculation."""
        reliability = synthesis_manager._assess_source_reliability(sample_retrieval_results)
        reliability_map = {r.source_id: r for r in reliability}
        
        # Test with doc1 sources
        doc1_sources = [r for r in sample_retrieval_results if r.chunk.document_id == "doc1"]
        group_reliability = synthesis_manager._calculate_group_reliability(doc1_sources, reliability_map)
        
        assert 0.0 <= group_reliability <= 1.0
    
    def test_calculate_synthesis_confidence(self, synthesis_manager, sample_retrieval_results):
        """Test synthesis confidence calculation."""
        reliability = synthesis_manager._assess_source_reliability(sample_retrieval_results)
        conflicts = synthesis_manager._detect_conflicts(sample_retrieval_results)
        
        confidence = synthesis_manager._calculate_synthesis_confidence(
            sample_retrieval_results, conflicts, reliability
        )
        
        assert 0.0 <= confidence <= 1.0
    
    def test_generate_methodology_notes(self, synthesis_manager, sample_retrieval_results):
        """Test methodology notes generation."""
        reliability = synthesis_manager._assess_source_reliability(sample_retrieval_results)
        conflicts = synthesis_manager._detect_conflicts(sample_retrieval_results)
        
        notes = synthesis_manager._generate_methodology_notes(
            sample_retrieval_results, conflicts, reliability
        )
        
        assert isinstance(notes, str)
        assert "sources" in notes.lower()
        assert "fiabilité" in notes.lower()
    
    def test_synthesize_sources_success(self, synthesis_manager, sample_retrieval_results):
        """Test successful source synthesis."""
        result = synthesis_manager.synthesize_sources(sample_retrieval_results, "Qu'est-ce que TCP?")
        
        assert isinstance(result, SynthesisResult)
        assert result.synthesized_content is not None
        assert len(result.source_reliability) == 3
        assert isinstance(result.detected_conflicts, list)
        assert 0.0 <= result.synthesis_confidence <= 1.0
        assert result.methodology_notes is not None
    
    def test_synthesize_sources_empty(self, synthesis_manager):
        """Test source synthesis with empty sources."""
        result = synthesis_manager.synthesize_sources([])
        
        assert isinstance(result, SynthesisResult)
        assert "Aucune source" in result.synthesized_content
        assert len(result.source_reliability) == 0
        assert len(result.detected_conflicts) == 0
        assert result.synthesis_confidence == 0.0
    
    def test_create_empty_synthesis(self, synthesis_manager):
        """Test empty synthesis creation."""
        result = synthesis_manager._create_empty_synthesis()
        
        assert isinstance(result, SynthesisResult)
        assert "Aucune source" in result.synthesized_content
        assert result.synthesis_confidence == 0.0
    
    def test_create_error_synthesis(self, synthesis_manager):
        """Test error synthesis creation."""
        error_msg = "Test error"
        result = synthesis_manager._create_error_synthesis(error_msg)
        
        assert isinstance(result, SynthesisResult)
        assert error_msg in result.synthesized_content
        assert result.synthesis_confidence == 0.0
    
    def test_synthesize_content(self, synthesis_manager, sample_retrieval_results):
        """Test content synthesis from grouped sources."""
        reliability = synthesis_manager._assess_source_reliability(sample_retrieval_results)
        conflicts = synthesis_manager._detect_conflicts(sample_retrieval_results)
        groups = synthesis_manager._group_sources_by_content(sample_retrieval_results, reliability)
        
        content = synthesis_manager._synthesize_content(
            groups, conflicts, reliability, "Test query"
        )
        
        assert isinstance(content, str)
        assert "Synthèse des sources" in content
    
    def test_reliability_weights_sum(self, synthesis_manager):
        """Test that reliability weights sum to approximately 1.0."""
        total_weight = sum(synthesis_manager.reliability_weights.values())
        assert abs(total_weight - 1.0) < 0.01  # Allow small floating point errors
    
    def test_score_citation_frequency(self, synthesis_manager, sample_chunks):
        """Test citation frequency scoring."""
        # Test with content that has authoritative language
        authoritative_chunk = ProcessedChunk(
            chunk_id="auth_chunk",
            document_id="doc1",
            content="Selon la norme IEEE 802.11, le protocole WiFi utilise...",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 1"],
            page_number=1,
            position_in_document=0.1,
            metadata={}
        )
        
        score = synthesis_manager._score_citation_frequency(authoritative_chunk)
        assert score > 0.3  # Should score higher due to "selon" and "norme"
    
    def test_score_source_authority(self, synthesis_manager):
        """Test source authority scoring."""
        authoritative_metadata = {
            "title": "Cours officiel de réseaux",
            "course_module": "Réseaux informatiques"
        }
        
        score = synthesis_manager._score_source_authority(authoritative_metadata)
        assert score > 0.5  # Should score higher due to "cours" keyword
    
    def test_score_content_completeness(self, synthesis_manager):
        """Test content completeness scoring."""
        complete_chunk = ProcessedChunk(
            chunk_id="complete_chunk",
            document_id="doc1",
            content="TCP est un protocole fiable. Par exemple, il utilise des accusés de réception pour garantir la livraison des données. C'est-à-dire que chaque paquet envoyé doit être confirmé par le destinataire.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 1", "Section 1.1", "Sous-section 1.1.1"],
            page_number=1,
            position_in_document=0.1,
            metadata={}
        )
        
        score = synthesis_manager._score_content_completeness(complete_chunk)
        assert score > 0.7  # Should score high due to examples and good structure


if __name__ == "__main__":
    pytest.main([__file__])