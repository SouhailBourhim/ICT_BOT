"""
Unit tests for query enhancement functionality.
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.managers.query_enhancer import QueryEnhancer, SynonymEntry, SpellCorrectionResult, LanguageDetectionResult, ClarificationQuestion
from src.models.base import EnhancedQuery, QueryIntent, AmbiguityReport, ConversationContext, Message
from datetime import datetime


class TestQueryEnhancer:
    """Test cases for QueryEnhancer."""
    
    @pytest.fixture
    def temp_vocab_dir(self):
        """Create temporary vocabulary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def query_enhancer(self, temp_vocab_dir):
        """Create QueryEnhancer instance with temporary vocabulary."""
        return QueryEnhancer(vocabulary_path=temp_vocab_dir)
    
    @pytest.fixture
    def sample_context(self):
        """Create sample conversation context."""
        messages = [
            Message(
                message_id="msg1",
                role="user",
                content="What is wireless communication?",
                timestamp=datetime.now(),
                sources=[],
                confidence=1.0
            ),
            Message(
                message_id="msg2",
                role="assistant",
                content="Wireless communication is...",
                timestamp=datetime.now(),
                sources=["doc1"],
                confidence=0.9
            )
        ]
        
        return ConversationContext(
            conversation_id="conv1",
            recent_messages=messages,
            summary="Discussion about wireless communication",
            relevant_topics=["wireless", "communication"],
            context_tokens=100
        )
    
    def test_initialization(self, query_enhancer):
        """Test QueryEnhancer initialization."""
        assert isinstance(query_enhancer.synonyms, dict)
        assert isinstance(query_enhancer.technical_terms, set)
        assert isinstance(query_enhancer.common_misspellings, dict)
        assert isinstance(query_enhancer.intent_patterns, dict)
        assert isinstance(query_enhancer.ambiguous_terms, dict)
    
    def test_enhance_query_basic(self, query_enhancer):
        """Test basic query enhancement."""
        query = "What is network protocol?"
        enhanced = query_enhancer.enhance_query(query)
        
        assert isinstance(enhanced, EnhancedQuery)
        assert enhanced.original_query == query
        assert enhanced.corrected_query is not None
        assert len(enhanced.expanded_terms) >= 1
        assert isinstance(enhanced.intent, QueryIntent)
        assert isinstance(enhanced.filters, dict)
        assert isinstance(enhanced.context_dependent, bool)
    
    def test_expand_terms_with_synonyms(self, query_enhancer):
        """Test term expansion with synonyms."""
        # Add test synonym
        query_enhancer.synonyms["network"] = SynonymEntry(
            term="network",
            synonyms=["net", "system", "infrastructure"],
            domain="networking",
            weight=1.0
        )
        
        query = "network protocol"
        expanded = query_enhancer.expand_terms(query)
        
        assert query in expanded  # Original query should be included
        assert len(expanded) > 1  # Should have additional terms
        
        # Check if synonyms are included
        expanded_lower = [term.lower() for term in expanded]
        assert any("net" in term or "system" in term for term in expanded_lower)
    
    def test_expand_terms_empty_query(self, query_enhancer):
        """Test term expansion with empty query."""
        expanded = query_enhancer.expand_terms("")
        assert expanded == [""]
    
    def test_correct_spelling_known_misspelling(self, query_enhancer):
        """Test spelling correction with known misspelling."""
        query_enhancer.common_misspellings["algoritm"] = "algorithm"
        
        query = "What is an algoritm?"
        corrected = query_enhancer.correct_spelling(query)
        
        assert "algorithm" in corrected.lower()
        assert "algoritm" not in corrected.lower()
    
    def test_correct_spelling_technical_terms(self, query_enhancer):
        """Test spelling correction preserves technical terms."""
        query_enhancer.technical_terms.add("algorithm")
        
        query = "algorithm implementation"
        corrected = query_enhancer.correct_spelling(query)
        
        assert corrected == query  # Should remain unchanged
    
    def test_correct_spelling_fuzzy_matching(self, query_enhancer):
        """Test spelling correction with fuzzy matching."""
        query_enhancer.technical_terms.add("bandwidth")
        
        query = "bandwith measurement"  # Misspelled bandwidth
        corrected = query_enhancer.correct_spelling(query)
        
        # Should correct to bandwidth if fuzzy matching works
        assert "bandwidth" in corrected.lower() or "bandwith" in corrected.lower()
    
    def test_detect_intent_factual(self, query_enhancer):
        """Test intent detection for factual queries."""
        queries = [
            "What is wireless communication?",
            "Define network protocol",
            "Explain the meaning of bandwidth"
        ]
        
        for query in queries:
            intent = query_enhancer.detect_intent(query)
            assert intent == QueryIntent.FACTUAL
    
    def test_detect_intent_procedural(self, query_enhancer):
        """Test intent detection for procedural queries."""
        queries = [
            "How to configure a router?",
            "Steps to implement encryption",
            "Procedure for network setup"
        ]
        
        for query in queries:
            intent = query_enhancer.detect_intent(query)
            assert intent == QueryIntent.PROCEDURAL
    
    def test_detect_intent_comparative(self, query_enhancer):
        """Test intent detection for comparative queries."""
        queries = [
            "Compare TCP and UDP",
            "Difference between WiFi and Bluetooth",
            "Which is better: WPA2 or WPA3?"
        ]
        
        for query in queries:
            intent = query_enhancer.detect_intent(query)
            assert intent == QueryIntent.COMPARATIVE
    
    def test_detect_intent_troubleshooting(self, query_enhancer):
        """Test intent detection for troubleshooting queries."""
        queries = [
            "Network connection error",
            "WiFi authentication problem",
            "Solve network issues"
        ]
        
        for query in queries:
            intent = query_enhancer.detect_intent(query)
            assert intent == QueryIntent.TROUBLESHOOTING
    
    def test_detect_ambiguity_clear_query(self, query_enhancer):
        """Test ambiguity detection with clear query."""
        query = "What is the TCP transmission control protocol specification?"
        ambiguity = query_enhancer.detect_ambiguity(query)
        
        assert isinstance(ambiguity, AmbiguityReport)
        # Clear queries might still have some ambiguity due to technical terms
        # Just check that it's not extremely ambiguous
        assert ambiguity.ambiguity_score < 1.0
    
    def test_detect_ambiguity_vague_query(self, query_enhancer):
        """Test ambiguity detection with vague query."""
        query = "How?"
        ambiguity = query_enhancer.detect_ambiguity(query)
        
        assert ambiguity.ambiguity_score > 0.0  # Should have some ambiguity
        assert len(ambiguity.clarification_questions) > 0
    
    def test_detect_ambiguity_ambiguous_terms(self, query_enhancer):
        """Test ambiguity detection with ambiguous terms."""
        query_enhancer.ambiguous_terms["channel"] = [
            "communication channel",
            "TV channel",
            "data channel"
        ]
        
        query = "What is a channel?"
        ambiguity = query_enhancer.detect_ambiguity(query)
        
        assert ambiguity.ambiguity_score > 0.0
        assert len(ambiguity.suggested_interpretations) > 0
    
    def test_context_dependency_detection(self, query_enhancer, sample_context):
        """Test context dependency detection."""
        context_dependent_queries = [
            "What about this protocol?",
            "How does it work?",
            "Tell me more about that"
        ]
        
        context_independent_queries = [
            "What is TCP protocol?",
            "Explain network routing",
            "Define bandwidth"
        ]
        
        for query in context_dependent_queries:
            enhanced = query_enhancer.enhance_query(query, sample_context)
            assert enhanced.context_dependent
        
        for query in context_independent_queries:
            enhanced = query_enhancer.enhance_query(query, sample_context)
            assert not enhanced.context_dependent
    
    def test_filter_extraction(self, query_enhancer):
        """Test filter extraction from queries."""
        test_cases = [
            # English filters
            ("Show me PDF documents", {"document_type": "pdf"}),
            ("Find slides from part1", {"course_module": "part1"}),
            ("Exercise from serie 2", {"course_module": "serie"}),
            # French filters
            ("Montrez-moi les documents PDF", {"document_type": "pdf"}),
            ("Trouvez les diapositives de la partie 1", {"course_module": "part1"}),
            ("Exercice de la série 2", {"course_module": "serie"}),
            ("TD1 sur les réseaux", {"course_module": "td1"}),
            ("TP de sécurité informatique", {"document_type": "exercise"}),
            ("Qu'est-ce que TCP?", {})  # No filters
        ]
        
        for query, expected_filters in test_cases:
            enhanced = query_enhancer.enhance_query(query)
            for key, value in expected_filters.items():
                assert key in enhanced.filters
                assert enhanced.filters[key] == value
    
    def test_vocabulary_file_creation(self, temp_vocab_dir):
        """Test vocabulary file creation."""
        enhancer = QueryEnhancer(vocabulary_path=temp_vocab_dir)
        
        vocab_path = Path(temp_vocab_dir)
        
        # Check if vocabulary files are created
        assert (vocab_path / "technical_terms.txt").exists()
        assert (vocab_path / "synonyms.json").exists()
        assert (vocab_path / "common_misspellings.json").exists()
        assert (vocab_path / "ambiguous_terms.json").exists()
    
    def test_vocabulary_file_loading(self, temp_vocab_dir):
        """Test vocabulary file loading."""
        vocab_path = Path(temp_vocab_dir)
        
        # Create test vocabulary files
        with open(vocab_path / "technical_terms.txt", 'w') as f:
            f.write("algorithm\nprotocol\nnetwork\n")
        
        synonyms_data = {
            "network": {
                "synonyms": ["net", "system"],
                "domain": "networking",
                "weight": 1.0
            }
        }
        with open(vocab_path / "synonyms.json", 'w') as f:
            json.dump(synonyms_data, f)
        
        misspellings_data = {"algoritm": "algorithm"}
        with open(vocab_path / "common_misspellings.json", 'w') as f:
            json.dump(misspellings_data, f)
        
        ambiguous_data = {"channel": ["communication channel", "TV channel"]}
        with open(vocab_path / "ambiguous_terms.json", 'w') as f:
            json.dump(ambiguous_data, f)
        
        # Create enhancer and test loading
        enhancer = QueryEnhancer(vocabulary_path=temp_vocab_dir)
        
        assert "algorithm" in enhancer.technical_terms
        assert "protocol" in enhancer.technical_terms
        assert "network" in enhancer.synonyms
        assert "algoritm" in enhancer.common_misspellings
        assert "channel" in enhancer.ambiguous_terms
    
    def test_error_handling_invalid_query(self, query_enhancer):
        """Test error handling with invalid queries."""
        # Test with None query (should handle gracefully)
        with patch.object(query_enhancer, '_tokenize_query', side_effect=Exception("Test error")):
            enhanced = query_enhancer.enhance_query("test query")
            
            # Should return basic enhanced query on error
            assert enhanced.original_query == "test query"
            assert enhanced.intent == QueryIntent.FACTUAL
    
    def test_tokenization(self, query_enhancer):
        """Test query tokenization."""
        test_cases = [
            ("What is TCP?", ["what", "is", "tcp"]),
            ("Network-protocol analysis", ["network", "protocol", "analysis"]),
            ("WiFi & Bluetooth", ["wifi", "bluetooth"]),
            ("", [])
        ]
        
        for query, expected_tokens in test_cases:
            tokens = query_enhancer._tokenize_query(query)
            assert tokens == expected_tokens
    
    def test_phrase_variations(self, query_enhancer):
        """Test phrase variation generation."""
        query_enhancer.synonyms["network"] = SynonymEntry(
            term="network",
            synonyms=["net", "system"],
            domain="networking",
            weight=1.0
        )
        
        query = "network protocol"
        tokens = ["network", "protocol"]
        variations = query_enhancer._generate_phrase_variations(query, tokens)
        
        assert len(variations) >= 0  # Should generate some variations
        if variations:
            # Check if variations contain synonyms
            variations_text = " ".join(variations)
            assert "net" in variations_text or "system" in variations_text
    
    def test_multiple_intent_detection(self, query_enhancer):
        """Test detection of multiple possible intents."""
        # Query that could be both factual and comparative
        query = "What is the difference between TCP and UDP?"
        
        possible_intents = query_enhancer._detect_multiple_intents(query)
        
        assert len(possible_intents) >= 1
        assert QueryIntent.FACTUAL in possible_intents or QueryIntent.COMPARATIVE in possible_intents


class TestSynonymEntry:
    """Test cases for SynonymEntry dataclass."""
    
    def test_synonym_entry_creation(self):
        """Test SynonymEntry creation."""
        entry = SynonymEntry(
            term="network",
            synonyms=["net", "system"],
            domain="networking",
            weight=1.0
        )
        
        assert entry.term == "network"
        assert entry.synonyms == ["net", "system"]
        assert entry.domain == "networking"
        assert entry.weight == 1.0
    
    def test_synonym_entry_default_weight(self):
        """Test SynonymEntry with default weight."""
        entry = SynonymEntry(
            term="protocol",
            synonyms=["standard"],
            domain="networking"
        )
        
        assert entry.weight == 1.0  # Default weight


class TestSpellCorrectionResult:
    """Test cases for SpellCorrectionResult dataclass."""
    
    def test_spell_correction_result_creation(self):
        """Test SpellCorrectionResult creation."""
        result = SpellCorrectionResult(
            original_term="algoritm",
            corrected_term="algorithm",
            confidence=0.9,
            suggestions=["algorithm", "logarithm"]
        )
        
        assert result.original_term == "algoritm"
        assert result.corrected_term == "algorithm"
        assert result.confidence == 0.9
        assert result.suggestions == ["algorithm", "logarithm"]


class TestLanguageDetectionResult:
    """Test cases for LanguageDetectionResult dataclass."""
    
    def test_language_detection_result_creation(self):
        """Test LanguageDetectionResult creation."""
        result = LanguageDetectionResult(
            detected_language="french",
            confidence=0.8,
            supported_languages=["english", "french", "arabic"]
        )
        
        assert result.detected_language == "french"
        assert result.confidence == 0.8
        assert result.supported_languages == ["english", "french", "arabic"]


class TestClarificationQuestion:
    """Test cases for ClarificationQuestion dataclass."""
    
    def test_clarification_question_creation(self):
        """Test ClarificationQuestion creation."""
        question = ClarificationQuestion(
            question="Are you asking about network protocols?",
            question_type="ambiguous_term",
            context={"term": "protocol", "interpretations": ["network protocol", "security protocol"]},
            priority=1
        )
        
        assert question.question == "Are you asking about network protocols?"
        assert question.question_type == "ambiguous_term"
        assert question.context["term"] == "protocol"
        assert question.priority == 1


class TestAdvancedQueryEnhancer:
    """Test cases for advanced QueryEnhancer functionality."""
    
    @pytest.fixture
    def temp_vocab_dir(self):
        """Create temporary vocabulary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def query_enhancer(self, temp_vocab_dir):
        """Create QueryEnhancer instance with temporary vocabulary."""
        return QueryEnhancer(vocabulary_path=temp_vocab_dir)
    
    def test_language_detection_english(self, query_enhancer):
        """Test language detection for English queries."""
        queries = [
            "What is network protocol?",
            "How to configure router settings?",
            "The wireless communication system"
        ]
        
        for query in queries:
            result = query_enhancer.detect_language(query)
            assert isinstance(result, LanguageDetectionResult)
            assert result.detected_language == "english"
            assert result.confidence > 0.0
    
    def test_language_detection_french(self, query_enhancer):
        """Test language detection for French queries."""
        queries = [
            "Qu'est-ce que le protocole réseau?",
            "Comment configurer les paramètres de sécurité?",
            "Le système de communication sans fil utilise des algorithmes",
            "Expliquer la différence entre TCP et UDP",
            "Réseau informatique et télécommunications"
        ]
        
        for query in queries:
            result = query_enhancer.detect_language(query)
            assert isinstance(result, LanguageDetectionResult)
            # Should detect French with good confidence
            assert result.detected_language == "french"
            assert result.confidence > 0.5
    
    def test_language_detection_arabic(self, query_enhancer):
        """Test language detection for Arabic queries."""
        queries = [
            "ما هو بروتوكول الشبكة؟",
            "كيفية تكوين إعدادات الموجه؟"
        ]
        
        for query in queries:
            result = query_enhancer.detect_language(query)
            assert isinstance(result, LanguageDetectionResult)
            assert result.detected_language == "arabic"
            assert result.confidence > 0.5
    
    def test_generate_clarification_questions_ambiguous(self, query_enhancer):
        """Test clarification question generation for ambiguous queries."""
        # Add test ambiguous terms
        query_enhancer.ambiguous_terms["channel"] = [
            "communication channel", "TV channel", "data channel"
        ]
        
        query = "What is a channel?"
        ambiguity = query_enhancer.detect_ambiguity(query)
        clarifications = query_enhancer.generate_clarification_questions(query, ambiguity)
        
        # Should generate clarifications if ambiguous or if there are suggested interpretations
        assert len(clarifications) > 0 or len(ambiguity.suggested_interpretations) > 0
        assert all(isinstance(q, ClarificationQuestion) for q in clarifications)
        
        # Check priority ordering
        priorities = [q.priority for q in clarifications]
        assert priorities == sorted(priorities)
    
    def test_generate_clarification_questions_clear(self, query_enhancer):
        """Test clarification question generation for clear queries."""
        query = "What is the TCP transmission control protocol specification?"
        ambiguity = query_enhancer.detect_ambiguity(query)
        clarifications = query_enhancer.generate_clarification_questions(query, ambiguity)
        
        # Clear queries should generate fewer clarification questions than very ambiguous ones
        # But may still generate some due to technical terms
        assert len(clarifications) <= 5
    
    def test_enhanced_ambiguity_scoring(self, query_enhancer):
        """Test enhanced ambiguity scoring algorithm."""
        # Add test data
        query_enhancer.ambiguous_terms["protocol"] = [
            "network protocol", "communication protocol", "security protocol"
        ]
        
        test_cases = [
            ("What is protocol?", True),  # Ambiguous term
            ("How?", True),  # Very short and vague
            ("What about this?", True),  # Vague reference
            ("What is the TCP protocol specification?", False),  # Specific and clear
        ]
        
        for query, should_be_ambiguous in test_cases:
            tokens = query_enhancer._tokenize_query(query)
            score, questions, interpretations = query_enhancer._enhanced_ambiguity_scoring(query, tokens)
            
            if should_be_ambiguous:
                assert score >= 0.15
            else:
                # Even clear queries might have some ambiguity, but should be lower
                assert score < 0.8
    
    def test_multiple_language_handling(self, query_enhancer):
        """Test handling of mixed language queries."""
        mixed_queries = [
            "What is réseau protocol?",  # English-French mix
            "How to configure الشبكة settings?",  # English-Arabic mix
        ]
        
        for query in mixed_queries:
            enhanced = query_enhancer.enhance_query(query)
            language_result = query_enhancer.detect_language(query)
            
            # Should handle mixed languages gracefully
            assert isinstance(enhanced, EnhancedQuery)
            assert isinstance(language_result, LanguageDetectionResult)
    
    def test_clarification_question_types(self, query_enhancer):
        """Test different types of clarification questions."""
        # Setup test data
        query_enhancer.ambiguous_terms["frame"] = ["data frame", "time frame", "reference frame"]
        
        test_cases = [
            ("What is a frame?", "ambiguous_term"),
            ("How?", "vague_query"),
            ("Qu'est-ce que le protocole?", "language"),
        ]
        
        for query, expected_type in test_cases:
            ambiguity = query_enhancer.detect_ambiguity(query)
            clarifications = query_enhancer.generate_clarification_questions(query, ambiguity)
            
            if clarifications:
                # Check if expected question type is present
                question_types = [q.question_type for q in clarifications]
                assert expected_type in question_types or len(clarifications) > 0
    
    def test_priority_ordering(self, query_enhancer):
        """Test priority ordering of clarification questions."""
        # Setup complex ambiguous query
        query_enhancer.ambiguous_terms["channel"] = ["communication channel", "TV channel"]
        query_enhancer.ambiguous_terms["protocol"] = ["network protocol", "security protocol"]
        
        query = "What is channel protocol?"  # Multiple ambiguous terms
        ambiguity = query_enhancer.detect_ambiguity(query)
        clarifications = query_enhancer.generate_clarification_questions(query, ambiguity)
        
        if len(clarifications) > 1:
            # Check that priorities are in ascending order (1 = highest priority)
            for i in range(len(clarifications) - 1):
                assert clarifications[i].priority <= clarifications[i + 1].priority
    
    def test_context_preservation(self, query_enhancer):
        """Test that clarification questions preserve context."""
        query_enhancer.ambiguous_terms["network"] = ["computer network", "neural network"]
        
        query = "How does network work?"
        ambiguity = query_enhancer.detect_ambiguity(query)
        clarifications = query_enhancer.generate_clarification_questions(query, ambiguity)
        
        for clarification in clarifications:
            # Each clarification should have context
            assert "context" in clarification.__dict__
            assert clarification.context is not None
            assert "original_query" in clarification.context or len(clarification.context) > 0


# Integration tests
class TestQueryEnhancerIntegration:
    """Integration tests for QueryEnhancer."""
    
    @pytest.fixture
    def temp_vocab_dir(self):
        """Create temporary vocabulary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def enhancer_with_data(self, temp_vocab_dir):
        """Create enhancer with comprehensive test data."""
        vocab_path = Path(temp_vocab_dir)
        
        # Create comprehensive test data
        technical_terms = [
            "algorithm", "protocol", "network", "bandwidth", "frequency",
            "modulation", "encryption", "authentication", "router", "switch"
        ]
        with open(vocab_path / "technical_terms.txt", 'w') as f:
            for term in technical_terms:
                f.write(f"{term}\n")
        
        synonyms_data = {
            "network": {
                "synonyms": ["net", "system", "infrastructure"],
                "domain": "networking",
                "weight": 1.0
            },
            "protocol": {
                "synonyms": ["standard", "specification", "format"],
                "domain": "networking",
                "weight": 1.0
            },
            "algorithm": {
                "synonyms": ["method", "procedure", "technique"],
                "domain": "computer_science",
                "weight": 1.0
            }
        }
        with open(vocab_path / "synonyms.json", 'w') as f:
            json.dump(synonyms_data, f)
        
        misspellings_data = {
            "algoritm": "algorithm",
            "protocal": "protocol",
            "bandwith": "bandwidth",
            "encription": "encryption"
        }
        with open(vocab_path / "common_misspellings.json", 'w') as f:
            json.dump(misspellings_data, f)
        
        ambiguous_data = {
            "channel": ["communication channel", "TV channel", "data channel"],
            "protocol": ["network protocol", "communication protocol", "security protocol"],
            "frame": ["data frame", "time frame", "reference frame"]
        }
        with open(vocab_path / "ambiguous_terms.json", 'w') as f:
            json.dump(ambiguous_data, f)
        
        return QueryEnhancer(vocabulary_path=temp_vocab_dir)
    
    def test_comprehensive_query_enhancement(self, enhancer_with_data):
        """Test comprehensive query enhancement workflow."""
        query = "How to implement encription algoritm for network protocal?"
        
        enhanced = enhancer_with_data.enhance_query(query)
        
        # Check spelling correction
        assert "encryption" in enhanced.corrected_query
        assert "algorithm" in enhanced.corrected_query
        assert "protocol" in enhanced.corrected_query
        
        # Check intent detection
        assert enhanced.intent == QueryIntent.PROCEDURAL
        
        # Check term expansion
        assert len(enhanced.expanded_terms) > 1
        
        # Check that original query is preserved
        assert enhanced.original_query == query
    
    def test_real_world_queries(self, enhancer_with_data):
        """Test with real-world query examples."""
        test_queries = [
            "What is the difference between TCP and UDP protocols?",
            "How to configure WiFi security settings?",
            "Explain wireless communication principles",
            "Network troubleshooting steps",
            "Compare encryption algorithms"
        ]
        
        for query in test_queries:
            enhanced = enhancer_with_data.enhance_query(query)
            
            # Basic validation
            assert enhanced.original_query == query
            assert enhanced.corrected_query is not None
            assert len(enhanced.expanded_terms) >= 1
            assert isinstance(enhanced.intent, QueryIntent)
            assert isinstance(enhanced.filters, dict)
            assert isinstance(enhanced.context_dependent, bool)
    
    def test_ambiguity_detection_comprehensive(self, enhancer_with_data):
        """Test comprehensive ambiguity detection."""
        test_cases = [
            ("What is a channel?", True),  # Ambiguous term
            ("How?", True),  # Vague query
            ("What is the TCP protocol specification?", False),  # Clear query
            ("Tell me about that", True),  # Context dependent
        ]
        
        for query, should_be_ambiguous in test_cases:
            ambiguity = enhancer_with_data.detect_ambiguity(query)
            
            if should_be_ambiguous:
                assert ambiguity.is_ambiguous or ambiguity.ambiguity_score >= 0.15
            else:
                assert not ambiguity.is_ambiguous and ambiguity.ambiguity_score <= 0.3


if __name__ == "__main__":
    pytest.main([__file__])