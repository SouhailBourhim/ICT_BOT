"""
Unit tests for advanced follow-up question detection.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from managers.followup_detector import FollowUpDetector
from models.base import Message, ConversationContext


class TestFollowUpDetector:
    """Test cases for FollowUpDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create FollowUpDetector instance."""
        return FollowUpDetector()
    
    @pytest.fixture
    def sample_context(self):
        """Create sample conversation context."""
        messages = [
            Message(
                message_id="msg_1",
                role="user",
                content="What is machine learning?",
                timestamp=datetime.now() - timedelta(minutes=2),
                sources=[],
                confidence=0.8
            ),
            Message(
                message_id="msg_2",
                role="assistant",
                content="Machine learning is a subset of artificial intelligence that enables computers to learn from data.",
                timestamp=datetime.now() - timedelta(minutes=1),
                sources=["textbook.pdf"],
                confidence=0.9
            )
        ]
        
        return ConversationContext(
            conversation_id="test_conv",
            recent_messages=messages,
            summary="Discussion about machine learning",
            relevant_topics=["machine", "learning", "artificial", "intelligence"],
            context_tokens=100
        )
    
    def test_direct_followup_patterns(self, detector, sample_context):
        """Test detection of direct follow-up patterns."""
        followup_queries = [
            "What about deep learning?",
            "How about neural networks?",
            "Can you explain it more?",
            "Tell me more about this",
            "And supervised learning?",
            "Additionally, what is reinforcement learning?"
        ]
        
        for query in followup_queries:
            is_followup, confidence, details = detector.detect_followup(query, sample_context)
            assert is_followup, f"Failed to detect direct follow-up: {query}"
            assert confidence > 0.3, f"Low confidence for direct follow-up: {query}"
            assert 'linguistic_details' in details
    
    def test_reference_patterns(self, detector, sample_context):
        """Test detection of reference-based follow-ups."""
        reference_queries = [
            "It sounds complex",
            "This is interesting",
            "That makes sense",
            "They are useful",
            "These algorithms work well"
        ]
        
        for query in reference_queries:
            is_followup, confidence, details = detector.detect_followup(query, sample_context)
            assert is_followup, f"Failed to detect reference follow-up: {query}"
            assert details['linguistic_details']['pattern_matches']['reference']
    
    def test_continuation_patterns(self, detector, sample_context):
        """Test detection of continuation patterns."""
        continuation_queries = [
            "But how does it actually work?",
            "However, what are the limitations?",
            "Then what happens next?",
            "Why is it important though?"
        ]
        
        for query in continuation_queries:
            is_followup, confidence, details = detector.detect_followup(query, sample_context)
            assert is_followup, f"Failed to detect continuation follow-up: {query}"
            assert details['linguistic_details']['pattern_matches']['continuation']
    
    def test_comparative_patterns(self, detector, sample_context):
        """Test detection of comparative patterns."""
        comparative_queries = [
            "Compared to traditional programming?",
            "How is it different from statistics?",
            "Is it better than rule-based systems?",
            "What about versus deep learning?"
        ]
        
        for query in comparative_queries:
            is_followup, confidence, details = detector.detect_followup(query, sample_context)
            # Comparative patterns might not always trigger follow-up detection alone
            # Check if comparative patterns were detected in linguistic analysis
            comparative_matches = details['linguistic_details']['pattern_matches']['comparative']
            assert len(comparative_matches) > 0 or confidence > 0.3, f"Should detect comparative elements: {query}"
    
    def test_non_followup_queries(self, detector, sample_context):
        """Test that non-follow-up queries are correctly identified."""
        non_followup_queries = [
            "What is the weather today?",
            "Explain quantum computing in detail",
            "How do I install Python on my computer?",
            "What are the benefits of exercise?",
            "Can you help me with my homework on biology?"
        ]
        
        for query in non_followup_queries:
            is_followup, confidence, details = detector.detect_followup(query, sample_context)
            assert not is_followup, f"Incorrectly detected follow-up: {query}"
            assert confidence < 0.5, f"High confidence for non-follow-up: {query}"
    
    def test_question_detection(self, detector):
        """Test question detection functionality."""
        questions = [
            "What is AI?",
            "How does it work?",
            "Can you explain this?",
            "Is this correct?",
            "Do you understand?"
        ]
        
        non_questions = [
            "This is a statement.",
            "Machine learning is useful.",
            "I understand now.",
            "Thank you for the explanation."
        ]
        
        for question in questions:
            assert detector._is_question(question), f"Failed to detect question: {question}"
        
        for statement in non_questions:
            assert not detector._is_question(statement), f"Incorrectly detected question: {statement}"
    
    def test_incomplete_sentence_detection(self, detector):
        """Test incomplete sentence detection."""
        incomplete_sentences = [
            "And neural networks",
            "But what about",
            "Also",
            "How about deep learning",
            "What if we use"
        ]
        
        complete_sentences = [
            "What is machine learning?",
            "This is a complete sentence.",
            "How does this algorithm work?",
            "I understand the concept now."
        ]
        
        for incomplete in incomplete_sentences:
            assert detector._is_incomplete_sentence(incomplete), f"Failed to detect incomplete: {incomplete}"
        
        for complete in complete_sentences:
            assert not detector._is_incomplete_sentence(complete), f"Incorrectly detected incomplete: {complete}"
    
    def test_topic_continuity_calculation(self, detector):
        """Test topic continuity calculation."""
        # High continuity
        query1 = "What is machine learning?"
        query2 = "How does machine learning work?"
        score = detector._calculate_topic_continuity(query2, query1)
        assert score > 0.5, "Should detect high topic continuity"
        
        # Low continuity
        query3 = "What is the weather today?"
        score = detector._calculate_topic_continuity(query3, query1)
        assert score < 0.5, "Should detect low topic continuity"
    
    def test_temporal_score_calculation(self, detector):
        """Test temporal proximity scoring."""
        # Recent message (high score)
        recent_time = timedelta(seconds=30)
        score = detector._calculate_temporal_score(recent_time)
        assert score >= 0.8, "Recent messages should have high temporal score"
        
        # Old message (low score)
        old_time = timedelta(hours=2)
        score = detector._calculate_temporal_score(old_time)
        assert score <= 0.3, "Old messages should have low temporal score"
    
    def test_complexity_relationship(self, detector):
        """Test query complexity relationship analysis."""
        simple_query = "What is AI?"
        complex_query = "Can you provide a detailed explanation of artificial intelligence?"
        
        # Follow-up should be simpler or similar
        followup_query = "How does it work?"
        score = detector._calculate_complexity_relationship(followup_query, complex_query)
        assert score >= 0.4, "Simpler follow-up should score well"
        
        # Much more complex query should score lower
        very_complex = "Can you provide an extremely detailed technical explanation with mathematical formulations?"
        score = detector._calculate_complexity_relationship(very_complex, simple_query)
        assert score <= 0.3, "Much more complex query should score lower"
    
    def test_keyword_extraction(self, detector):
        """Test keyword extraction functionality."""
        text = "What is machine learning and how does it work in practice?"
        keywords = detector._extract_keywords(text)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "machine" in keywords
        assert "learning" in keywords
        assert "work" in keywords
        assert "practice" in keywords
        
        # Stop words should be filtered out
        assert "what" not in keywords
        assert "and" not in keywords
        assert "how" not in keywords
        assert "does" not in keywords
    
    def test_entity_extraction(self, detector):
        """Test entity extraction functionality."""
        text = "Machine learning and neural networks are part of artificial intelligence."
        entities = detector._extract_entities(text)
        
        assert isinstance(entities, list)
        assert len(entities) > 0
        
        # Should extract capitalized words
        assert "Machine" in entities
        
        # Should extract technical terms
        technical_terms = [entity.lower() for entity in entities]
        assert any("learning" in term for term in technical_terms)
        assert any("network" in term for term in technical_terms)
    
    def test_lexical_similarity(self, detector):
        """Test lexical similarity calculation."""
        text1 = "machine learning algorithms"
        text2 = "learning algorithms for machines"
        
        similarity = detector._calculate_lexical_similarity(text1, text2)
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.3, "Should detect reasonable similarity"
        
        # Completely different texts
        text3 = "weather forecast today"
        similarity = detector._calculate_lexical_similarity(text1, text3)
        assert similarity < 0.3, "Should detect low similarity"
    
    def test_relevant_context_messages(self, detector, sample_context):
        """Test extraction of relevant context messages."""
        query = "How does it work?"
        relevant_messages = detector._get_relevant_context_messages(
            sample_context.recent_messages, query
        )
        
        assert isinstance(relevant_messages, list)
        assert len(relevant_messages) > 0
        
        # Should include user messages
        user_messages = [msg for msg in relevant_messages if msg.role == "user"]
        assert len(user_messages) > 0
    
    def test_context_integration(self, detector, sample_context):
        """Test follow-up context integration."""
        followup_query = "How does it work?"
        
        integration = detector.get_followup_context_integration(followup_query, sample_context)
        
        assert isinstance(integration, dict)
        assert 'is_followup' in integration
        assert 'enhanced_query' in integration
        assert 'context_additions' in integration
        
        if integration['is_followup']:
            assert integration['confidence'] > 0.0
            assert len(integration['enhanced_query']) > len(followup_query)
            assert isinstance(integration['context_additions'], list)
    
    def test_empty_context_handling(self, detector):
        """Test handling of empty context."""
        empty_context = ConversationContext(
            conversation_id="empty",
            recent_messages=[],
            summary="",
            relevant_topics=[],
            context_tokens=0
        )
        
        is_followup, confidence, details = detector.detect_followup("What is AI?", empty_context)
        
        assert not is_followup
        assert confidence == 0.0
        assert details['reason'] == "no_context"
    
    def test_confidence_scoring_consistency(self, detector, sample_context):
        """Test that confidence scores are consistent and reasonable."""
        test_queries = [
            ("What about deep learning?", True),  # Clear follow-up
            ("How does it work?", True),  # Reference follow-up
            ("What is the weather today?", False),  # Completely different topic
            ("Thank you for the explanation.", False),  # Not a question
        ]
        
        for query, expected_followup in test_queries:
            is_followup, confidence, details = detector.detect_followup(query, sample_context)
            
            assert is_followup == expected_followup, f"Incorrect detection for: {query}"
            assert 0.0 <= confidence <= 1.0, f"Invalid confidence score: {confidence}"
            
            if expected_followup:
                assert confidence >= 0.3, f"Low confidence for expected follow-up: {query}"
            else:
                assert confidence < 0.5, f"High confidence for non-follow-up: {query}"
    
    def test_detection_details_structure(self, detector, sample_context):
        """Test that detection details have proper structure."""
        query = "What about neural networks?"
        is_followup, confidence, details = detector.detect_followup(query, sample_context)
        
        # Check required fields
        required_fields = [
            'linguistic_score', 'contextual_score', 'embedding_score',
            'combined_score', 'linguistic_details', 'contextual_details',
            'embedding_details', 'relevant_messages_count'
        ]
        
        for field in required_fields:
            assert field in details, f"Missing required field: {field}"
        
        # Check score ranges
        assert 0.0 <= details['linguistic_score'] <= 1.0
        assert 0.0 <= details['contextual_score'] <= 1.0
        assert 0.0 <= details['embedding_score'] <= 1.0
        assert 0.0 <= details['combined_score'] <= 1.0
        
        # Check linguistic details structure
        linguistic_details = details['linguistic_details']
        assert 'pattern_scores' in linguistic_details
        assert 'pattern_matches' in linguistic_details
        assert 'is_question' in linguistic_details
        assert 'word_count' in linguistic_details


if __name__ == "__main__":
    pytest.main([__file__])