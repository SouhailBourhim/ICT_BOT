"""
Synthesis Manager for multi-source information synthesis with conflict detection.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from src.models.base import RetrievalResult, ProcessedChunk, DocumentMetadata
from config.settings import get_settings


logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of conflicts between sources."""
    CONTRADICTORY = "contradictory"
    INCONSISTENT_DETAILS = "inconsistent_details"
    DIFFERENT_PERSPECTIVES = "different_perspectives"
    OUTDATED_INFORMATION = "outdated_information"
    SCOPE_DIFFERENCE = "scope_difference"


@dataclass
class SourceConflict:
    """Represents a conflict between sources."""
    conflict_type: ConflictType
    source_ids: List[str]
    conflicting_content: List[str]
    confidence: float
    description: str


@dataclass
class SourceReliability:
    """Reliability assessment for a source."""
    source_id: str
    reliability_score: float
    factors: Dict[str, float]  # Individual scoring factors
    metadata: Dict[str, Any]


@dataclass
class SynthesisResult:
    """Result of multi-source synthesis."""
    synthesized_content: str
    source_reliability: List[SourceReliability]
    detected_conflicts: List[SourceConflict]
    synthesis_confidence: float
    methodology_notes: str


class SynthesisManager:
    """
    Manages multi-source information synthesis with conflict detection and reliability scoring.
    """
    
    def __init__(self):
        """Initialize the synthesis manager."""
        self.settings = get_settings()
        
        # Conflict detection keywords and patterns
        self.contradiction_indicators = [
            "contrairement", "au contraire", "cependant", "néanmoins", "toutefois",
            "par contre", "en revanche", "à l'opposé", "différemment"
        ]
        
        self.uncertainty_indicators = [
            "peut-être", "probablement", "il semble", "apparemment", "selon",
            "d'après", "vraisemblablement", "possiblement"
        ]
        
        # Reliability factors and weights
        self.reliability_weights = {
            "document_age": 0.2,
            "document_type": 0.15,
            "content_quality": 0.25,
            "citation_frequency": 0.15,
            "source_authority": 0.15,
            "content_completeness": 0.1
        }
    
    def synthesize_sources(self, sources: List[RetrievalResult], 
                          query_context: str = "") -> SynthesisResult:
        """
        Synthesize information from multiple sources with conflict detection.
        
        Args:
            sources: List of retrieval results to synthesize
            query_context: Original query for context
            
        Returns:
            SynthesisResult with synthesized content and analysis
        """
        try:
            if not sources:
                return self._create_empty_synthesis()
            
            # Step 1: Assess source reliability
            source_reliability = self._assess_source_reliability(sources)
            
            # Step 2: Detect conflicts between sources
            conflicts = self._detect_conflicts(sources)
            
            # Step 3: Group sources by reliability and content similarity
            source_groups = self._group_sources_by_content(sources, source_reliability)
            
            # Step 4: Synthesize content considering reliability and conflicts
            synthesized_content = self._synthesize_content(
                source_groups, conflicts, source_reliability, query_context
            )
            
            # Step 5: Calculate overall synthesis confidence
            synthesis_confidence = self._calculate_synthesis_confidence(
                sources, conflicts, source_reliability
            )
            
            # Step 6: Generate methodology notes
            methodology_notes = self._generate_methodology_notes(
                sources, conflicts, source_reliability
            )
            
            return SynthesisResult(
                synthesized_content=synthesized_content,
                source_reliability=source_reliability,
                detected_conflicts=conflicts,
                synthesis_confidence=synthesis_confidence,
                methodology_notes=methodology_notes
            )
            
        except Exception as e:
            logger.error(f"Error in source synthesis: {e}")
            return self._create_error_synthesis(str(e))
    
    def _assess_source_reliability(self, sources: List[RetrievalResult]) -> List[SourceReliability]:
        """Assess reliability of each source."""
        reliability_scores = []
        
        for source in sources:
            chunk = source.chunk
            metadata = chunk.metadata
            
            # Calculate individual reliability factors
            factors = {
                "document_age": self._score_document_age(metadata),
                "document_type": self._score_document_type(metadata),
                "content_quality": self._score_content_quality(chunk),
                "citation_frequency": self._score_citation_frequency(chunk),
                "source_authority": self._score_source_authority(metadata),
                "content_completeness": self._score_content_completeness(chunk)
            }
            
            # Calculate weighted reliability score
            reliability_score = sum(
                factors[factor] * self.reliability_weights[factor]
                for factor in factors
            )
            
            reliability_scores.append(SourceReliability(
                source_id=chunk.chunk_id,
                reliability_score=reliability_score,
                factors=factors,
                metadata={
                    "document_title": metadata.get("title", "Unknown"),
                    "retrieval_score": source.score,
                    "retrieval_method": source.retrieval_method
                }
            ))
        
        return reliability_scores
    
    def _score_document_age(self, metadata: Dict[str, Any]) -> float:
        """Score based on document age (newer is generally better)."""
        try:
            # If no date available, assume moderate age
            if "creation_date" not in metadata:
                return 0.6
            
            creation_date = metadata["creation_date"]
            if isinstance(creation_date, str):
                # Try to parse date string
                try:
                    from dateutil.parser import parse
                    creation_date = parse(creation_date)
                except:
                    return 0.6
            
            # Calculate age in years
            age_years = (datetime.now() - creation_date).days / 365.25
            
            # Score: 1.0 for very recent, decreasing with age
            if age_years < 1:
                return 1.0
            elif age_years < 3:
                return 0.9
            elif age_years < 5:
                return 0.7
            elif age_years < 10:
                return 0.5
            else:
                return 0.3
                
        except Exception:
            return 0.6  # Default moderate score
    
    def _score_document_type(self, metadata: Dict[str, Any]) -> float:
        """Score based on document type reliability."""
        doc_type = metadata.get("document_type", "").lower()
        
        type_scores = {
            "pdf": 0.9,      # Usually formal documents
            "docx": 0.8,     # Structured documents
            "txt": 0.6,      # Plain text, variable quality
            "md": 0.7,       # Markdown, often documentation
            "html": 0.5      # Web content, variable quality
        }
        
        return type_scores.get(doc_type, 0.6)
    
    def _score_content_quality(self, chunk: ProcessedChunk) -> float:
        """Score based on content quality indicators."""
        content = chunk.content.lower()
        
        # Quality indicators
        quality_score = 0.5  # Base score
        
        # Positive indicators
        if len(content) > 100:  # Substantial content
            quality_score += 0.1
        if any(word in content for word in ["définition", "exemple", "formule"]):
            quality_score += 0.1
        if chunk.hierarchical_context:  # Well-structured
            quality_score += 0.1
        if content.count('.') > 2:  # Multiple sentences
            quality_score += 0.1
        
        # Negative indicators
        if any(phrase in content for phrase in self.uncertainty_indicators):
            quality_score -= 0.1
        if len(content) < 50:  # Very short content
            quality_score -= 0.2
        
        return max(0.0, min(1.0, quality_score))
    
    def _score_citation_frequency(self, chunk: ProcessedChunk) -> float:
        """Score based on how often this content might be cited."""
        # This is a simplified heuristic - in practice, you might track actual citations
        content = chunk.content.lower()
        
        # Look for authoritative language
        authoritative_phrases = [
            "selon", "d'après", "référence", "source", "étude", "recherche",
            "théorème", "loi", "principe", "standard", "norme"
        ]
        
        citation_indicators = sum(1 for phrase in authoritative_phrases if phrase in content)
        return min(1.0, citation_indicators * 0.2 + 0.3)
    
    def _score_source_authority(self, metadata: Dict[str, Any]) -> float:
        """Score based on source authority."""
        title = metadata.get("title", "").lower()
        course_module = metadata.get("course_module", "").lower()
        
        # Authority indicators in title
        authority_keywords = [
            "cours", "syllabus", "manuel", "guide", "référence", "standard",
            "norme", "spécification", "documentation officielle"
        ]
        
        authority_score = 0.5  # Base score
        
        for keyword in authority_keywords:
            if keyword in title:
                authority_score += 0.1
        
        # Course module context adds authority
        if course_module:
            authority_score += 0.1
        
        return min(1.0, authority_score)
    
    def _score_content_completeness(self, chunk: ProcessedChunk) -> float:
        """Score based on content completeness."""
        content = chunk.content
        
        # Completeness indicators
        completeness_score = 0.5
        
        # Has examples or explanations
        if any(word in content.lower() for word in ["exemple", "par exemple", "c'est-à-dire"]):
            completeness_score += 0.2
        
        # Has structured information
        if chunk.hierarchical_context and len(chunk.hierarchical_context) > 1:
            completeness_score += 0.1
        
        # Reasonable length
        if 200 <= len(content) <= 1500:
            completeness_score += 0.2
        
        return min(1.0, completeness_score)
    
    def _detect_conflicts(self, sources: List[RetrievalResult]) -> List[SourceConflict]:
        """Detect conflicts between sources."""
        conflicts = []
        
        # Compare each pair of sources
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                source1 = sources[i]
                source2 = sources[j]
                
                conflict = self._analyze_source_pair(source1, source2)
                if conflict:
                    conflicts.append(conflict)
        
        return conflicts
    
    def _analyze_source_pair(self, source1: RetrievalResult, 
                           source2: RetrievalResult) -> Optional[SourceConflict]:
        """Analyze a pair of sources for conflicts."""
        content1 = source1.chunk.content.lower()
        content2 = source2.chunk.content.lower()
        
        # Check for direct contradictions
        contradiction_score = self._detect_contradictions(content1, content2)
        
        if contradiction_score > 0.7:
            return SourceConflict(
                conflict_type=ConflictType.CONTRADICTORY,
                source_ids=[source1.chunk.chunk_id, source2.chunk.chunk_id],
                conflicting_content=[source1.chunk.content, source2.chunk.content],
                confidence=contradiction_score,
                description=f"Sources contain contradictory information (confidence: {contradiction_score:.2f})"
            )
        
        # Check for inconsistent details
        inconsistency_score = self._detect_inconsistencies(content1, content2)
        
        if inconsistency_score > 0.6:
            return SourceConflict(
                conflict_type=ConflictType.INCONSISTENT_DETAILS,
                source_ids=[source1.chunk.chunk_id, source2.chunk.chunk_id],
                conflicting_content=[source1.chunk.content, source2.chunk.content],
                confidence=inconsistency_score,
                description=f"Sources have inconsistent details (confidence: {inconsistency_score:.2f})"
            )
        
        return None
    
    def _detect_contradictions(self, content1: str, content2: str) -> float:
        """Detect contradictory statements between two contents."""
        # Simple heuristic: look for opposing statements
        contradiction_score = 0.0
        
        # Check for contradiction indicators
        has_contradiction_words = any(
            word in content1 or word in content2 
            for word in self.contradiction_indicators
        )
        
        if has_contradiction_words:
            contradiction_score += 0.3
        
        # Check for opposing numerical values or boolean statements
        # This is a simplified implementation
        opposing_pairs = [
            ("oui", "non"), ("vrai", "faux"), ("possible", "impossible"),
            ("toujours", "jamais"), ("tous", "aucun")
        ]
        
        for pos, neg in opposing_pairs:
            if pos in content1 and neg in content2:
                contradiction_score += 0.4
            elif neg in content1 and pos in content2:
                contradiction_score += 0.4
        
        return min(1.0, contradiction_score)
    
    def _detect_inconsistencies(self, content1: str, content2: str) -> float:
        """Detect inconsistent details between two contents."""
        # Look for different values for similar concepts
        inconsistency_score = 0.0
        
        # Check for uncertainty in one source but certainty in another
        uncertainty1 = any(phrase in content1 for phrase in self.uncertainty_indicators)
        uncertainty2 = any(phrase in content2 for phrase in self.uncertainty_indicators)
        
        if uncertainty1 != uncertainty2:
            inconsistency_score += 0.2
        
        # Check for different levels of detail (one very short, one detailed)
        length_ratio = len(content1) / max(len(content2), 1)
        if length_ratio > 3 or length_ratio < 0.33:
            inconsistency_score += 0.3
        
        return min(1.0, inconsistency_score)
    
    def _group_sources_by_content(self, sources: List[RetrievalResult], 
                                reliability: List[SourceReliability]) -> Dict[str, List[RetrievalResult]]:
        """Group sources by content similarity and reliability."""
        # Simple grouping by document for now
        # In a more sophisticated implementation, you might use semantic similarity
        
        groups = {}
        for source in sources:
            doc_id = source.chunk.document_id
            if doc_id not in groups:
                groups[doc_id] = []
            groups[doc_id].append(source)
        
        return groups
    
    def _synthesize_content(self, source_groups: Dict[str, List[RetrievalResult]], 
                          conflicts: List[SourceConflict],
                          reliability: List[SourceReliability],
                          query_context: str) -> str:
        """Synthesize content from grouped sources."""
        synthesis_parts = []
        
        # Create reliability lookup
        reliability_map = {r.source_id: r for r in reliability}
        
        # Sort groups by average reliability
        sorted_groups = sorted(
            source_groups.items(),
            key=lambda x: self._calculate_group_reliability(x[1], reliability_map),
            reverse=True
        )
        
        synthesis_parts.append("## Synthèse des sources\n")
        
        # Process each group
        for doc_id, sources in sorted_groups:
            if not sources:
                continue
                
            doc_title = sources[0].chunk.metadata.get("title", f"Document {doc_id}")
            avg_reliability = self._calculate_group_reliability(sources, reliability_map)
            
            synthesis_parts.append(f"\n### {doc_title} (Fiabilité: {avg_reliability:.2f})")
            
            # Combine content from this group
            group_content = []
            for source in sources:
                rel_score = reliability_map.get(source.chunk.chunk_id)
                if rel_score and rel_score.reliability_score > 0.5:
                    group_content.append(source.chunk.content)
            
            if group_content:
                synthesis_parts.append(" ".join(group_content))
        
        # Add conflict information if any
        if conflicts:
            synthesis_parts.append("\n## ⚠️ Conflits détectés entre les sources")
            for conflict in conflicts:
                synthesis_parts.append(f"\n- **{conflict.conflict_type.value}**: {conflict.description}")
        
        return "\n".join(synthesis_parts)
    
    def _calculate_group_reliability(self, sources: List[RetrievalResult], 
                                   reliability_map: Dict[str, SourceReliability]) -> float:
        """Calculate average reliability for a group of sources."""
        if not sources:
            return 0.0
        
        total_reliability = 0.0
        count = 0
        
        for source in sources:
            rel = reliability_map.get(source.chunk.chunk_id)
            if rel:
                total_reliability += rel.reliability_score
                count += 1
        
        return total_reliability / max(count, 1)
    
    def _calculate_synthesis_confidence(self, sources: List[RetrievalResult],
                                     conflicts: List[SourceConflict],
                                     reliability: List[SourceReliability]) -> float:
        """Calculate overall confidence in the synthesis."""
        if not sources:
            return 0.0
        
        # Base confidence from source reliability
        avg_reliability = sum(r.reliability_score for r in reliability) / len(reliability)
        
        # Reduce confidence based on conflicts
        conflict_penalty = len(conflicts) * 0.1
        
        # Reduce confidence if sources are very different in reliability
        reliability_scores = [r.reliability_score for r in reliability]
        reliability_variance = max(reliability_scores) - min(reliability_scores)
        variance_penalty = reliability_variance * 0.2
        
        # Calculate final confidence
        confidence = avg_reliability - conflict_penalty - variance_penalty
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_methodology_notes(self, sources: List[RetrievalResult],
                                  conflicts: List[SourceConflict],
                                  reliability: List[SourceReliability]) -> str:
        """Generate notes about the synthesis methodology."""
        notes = []
        
        notes.append(f"Synthèse basée sur {len(sources)} sources.")
        
        # Reliability distribution
        high_rel = sum(1 for r in reliability if r.reliability_score > 0.8)
        medium_rel = sum(1 for r in reliability if 0.5 <= r.reliability_score <= 0.8)
        low_rel = sum(1 for r in reliability if r.reliability_score < 0.5)
        
        notes.append(f"Fiabilité des sources: {high_rel} élevée, {medium_rel} moyenne, {low_rel} faible.")
        
        # Conflict information
        if conflicts:
            notes.append(f"{len(conflicts)} conflit(s) détecté(s) entre les sources.")
        else:
            notes.append("Aucun conflit majeur détecté entre les sources.")
        
        # Methodology
        notes.append("Méthodologie: Pondération par fiabilité, détection de conflits, synthèse hiérarchique.")
        
        return " ".join(notes)
    
    def _create_empty_synthesis(self) -> SynthesisResult:
        """Create empty synthesis result."""
        return SynthesisResult(
            synthesized_content="Aucune source disponible pour la synthèse.",
            source_reliability=[],
            detected_conflicts=[],
            synthesis_confidence=0.0,
            methodology_notes="Synthèse impossible: aucune source fournie."
        )
    
    def _create_error_synthesis(self, error_message: str) -> SynthesisResult:
        """Create error synthesis result."""
        return SynthesisResult(
            synthesized_content=f"Erreur lors de la synthèse: {error_message}",
            source_reliability=[],
            detected_conflicts=[],
            synthesis_confidence=0.0,
            methodology_notes=f"Erreur de synthèse: {error_message}"
        )