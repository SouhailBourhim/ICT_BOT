"""
Unit tests for enhanced context window management functionality.
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch

from src.managers.conversation_manager import ConversationManager
from src.models.base import Message, ConversationContext


class TestContextWindowManagement:
    """Test cases for enhanced context window management."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def conversation_manager(self, temp_db):
        """Create ConversationManager instance with temporary database."""
        return ConversationManager(db_path=temp_db)
    
    @pytest.fixture
    def sample_messages(self):
        """Create sample messages for testing."""
        messages = []
        base_time = datetime.now()
        
        # Create a conversation with various message types
        message_contents = [
            ("user", "What is machine learning?"),
            ("assistant", "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed. It involves algorithms that can identify patterns in data and make predictions or classifications based on those patterns."),
            ("user", "How does it work?"),
            ("assistant", "Machine learning works through several key steps: data collection, data preprocessing, model selection, training, and evaluation. The algorithm learns from training data to create a model that can make predictions on new, unseen data."),
            ("user", "What are the main types of machine learning?"),
            ("assistant", "There are three main types: supervised learning (learning with labeled data), unsupervised learning (finding patterns in unlabeled data), and reinforcement learning (learning through interaction and feedback)."),
            ("user", "Can you explain neural networks?"),
            ("assistant", "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes (neurons) organized in layers that process information and learn complex patterns through training."),
            ("user", "What about deep learning?"),
            ("assistant", "Deep learning is a subset of machine learning that uses neural networks with multiple hidden layers. It's particularly effective for tasks like image recognition, natural language processing, and speech recognition."),
        ]
        
        for i, (role, content) in enumerate(message_contents):
            message = Message(
                message_id=f"msg_{i}",
                role=role,
                content=content,
                timestamp=base_time + timedelta(minutes=i),
                sources=["textbook.pdf"] if role == "assistant" else [],
                confidence=0.9 if role == "assistant" else 0.8
            )
            messages.append(message)
        
        return messages
    
    def test_sliding_window_context_extraction(self, conversation_manager, sample_messages):
        """Test sliding window context extraction with token limits."""
        # Test with generous token limit
        selected_messages, token_count = conversation_manager._extract_sliding_window_context(
            sample_messages, max_tokens=1000
        )
        
        assert len(selected_messages) > 0
        assert token_count <= 1000
        assert selected_messages[-1] == sample_messages[-1]  # Most recent message included
    
    def test_sliding_window_with_tight_token_limit(self, conversation_manager, sample_messages):
        """Test sliding window with very tight token limit."""
        selected_messages, token_count = conversation_manager._extract_sliding_window_context(
            sample_messages, max_tokens=50
        )
        
        assert len(selected_messages) > 0
        assert token_count <= 50
        # Should include most recent messages within token limit
    
    def test_message_relevance_scoring(self, conversation_manager):
        """Test message relevance scoring algorithm."""
        # Create messages with different characteristics
        messages = [
            Message("msg1", "user", "What is AI?", datetime.now(), [], 0.8),
            Message("msg2", "assistant", "AI is artificial intelligence.", datetime.now(), ["source1"], 0.9),
            Message("msg3", "user", "How does machine learning work in detail?", datetime.now(), [], 0.8),
            Message("msg4", "assistant", "Machine learning works through complex algorithms.", datetime.now(), ["source2"], 0.95),
        ]
        
        # Test relevance scoring
        for i, message in enumerate(messages):
            score = conversation_manager._calculate_message_relevance(message, i, len(messages))
            assert 0.0 <= score <= 1.0
            
            # User messages with questions should score reasonably
            if message.role == "user" and "?" in message.content:
                assert score > 0.3  # Adjusted expectation
    
    def test_relevant_message_selection(self, conversation_manager, sample_messages):
        """Test selection of most relevant messages."""
        # Select top 3 most relevant messages
        selected = conversation_manager._select_relevant_messages(sample_messages, max_messages=3)
        
        assert len(selected) == 3
        # Should maintain chronological order
        for i in range(len(selected) - 1):
            assert selected[i].timestamp <= selected[i + 1].timestamp
        
        # Should include recent messages
        recent_message_ids = [msg.message_id for msg in sample_messages[-3:]]
        selected_ids = [msg.message_id for msg in selected]
        assert any(msg_id in selected_ids for msg_id in recent_message_ids)
    
    def test_token_estimation(self, conversation_manager):
        """Test token estimation accuracy."""
        test_texts = [
            "Hello world",  # Simple text
            "This is a longer sentence with more words to test token estimation.",  # Medium text
            "What is machine learning and how does it work in practice?",  # Question
            "",  # Empty text
        ]
        
        for text in test_texts:
            tokens = conversation_manager._estimate_tokens(text)
            assert tokens >= 1  # Should always return at least 1 token
            if text:
                # Rough validation: should be reasonable for text length
                assert tokens <= len(text.split()) * 2  # Upper bound check
    
    def test_text_truncation(self, conversation_manager):
        """Test text truncation to token limits."""
        long_text = "This is a very long text that needs to be truncated to fit within token limits. " * 10
        
        truncated = conversation_manager._truncate_to_tokens(long_text, max_tokens=20)
        
        assert len(truncated) < len(long_text)
        assert truncated.endswith("...") or len(truncated.split()) <= 20
        
        # Test with very small limit
        truncated_small = conversation_manager._truncate_to_tokens(long_text, max_tokens=1)
        assert len(truncated_small.split()) <= 3  # Should be very short
    
    def test_enhanced_context_extraction(self, conversation_manager, sample_messages):
        """Test complete enhanced context extraction."""
        # Create conversation and add messages
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        for message in sample_messages:
            conversation_manager.add_message(conversation_id, message)
        
        # Test context extraction with different token limits
        context_small = conversation_manager.get_context(conversation_id, max_tokens=100)
        context_large = conversation_manager.get_context(conversation_id, max_tokens=2000)
        
        # Verify context structure
        assert context_small.conversation_id == conversation_id
        assert context_large.conversation_id == conversation_id
        
        # Small context should have fewer messages
        assert len(context_small.recent_messages) <= len(context_large.recent_messages)
        
        # Token counts should respect limits
        assert context_small.context_tokens <= 100
        assert context_large.context_tokens <= 2000
        
        # Should extract relevant topics
        assert isinstance(context_large.relevant_topics, list)
        assert len(context_large.relevant_topics) > 0
    
    def test_conversation_turn_grouping(self, conversation_manager, sample_messages):
        """Test grouping messages into conversation turns."""
        turns = conversation_manager._group_into_turns(sample_messages)
        
        assert len(turns) > 0
        
        # Each turn should have user and assistant messages
        for turn in turns:
            assert 'user' in turn
            assert 'assistant' in turn
            assert len(turn['user']) > 0
            assert len(turn['assistant']) > 0
    
    def test_conversation_topic_extraction(self, conversation_manager, sample_messages):
        """Test enhanced topic extraction from conversation."""
        topics = conversation_manager._extract_conversation_topics(sample_messages)
        
        assert isinstance(topics, list)
        assert len(topics) > 0
        
        # Should extract relevant technical terms
        topic_text = " ".join(topics).lower()
        expected_terms = ["machine", "learning", "neural", "networks"]
        assert any(term in topic_text for term in expected_terms)
    
    def test_turn_importance_scoring(self, conversation_manager):
        """Test conversation turn importance scoring."""
        # Create turns with different characteristics
        turns = [
            {"user": "Hi", "assistant": "Hello"},  # Simple greeting
            {"user": "What is machine learning?", "assistant": "Machine learning is a complex field..."},  # Technical question
            {"user": "How does neural network training work?", "assistant": "Neural network training involves..."},  # Complex technical
        ]
        
        scores = []
        for i, turn in enumerate(turns):
            score = conversation_manager._calculate_turn_importance(turn, i, len(turns))
            scores.append(score)
            assert 0.0 <= score <= 1.0
        
        # Technical questions should score higher than simple greetings
        assert scores[1] > scores[0]
        assert scores[2] > scores[0]
    
    def test_important_turn_selection(self, conversation_manager, sample_messages):
        """Test selection of important conversation turns."""
        turns = conversation_manager._group_into_turns(sample_messages)
        
        # Select top 2 most important turns
        important_turns = conversation_manager._select_important_turns(turns, max_turns=2)
        
        assert len(important_turns) == 2
        
        # Should maintain chronological order
        turn_positions = []
        for selected_turn in important_turns:
            for i, original_turn in enumerate(turns):
                if (selected_turn['user'] == original_turn['user'] and 
                    selected_turn['assistant'] == original_turn['assistant']):
                    turn_positions.append(i)
                    break
        
        assert turn_positions == sorted(turn_positions)
    
    def test_key_sentence_extraction(self, conversation_manager):
        """Test extraction of key sentences from text."""
        test_texts = [
            "This is a simple sentence.",
            "What is machine learning? It is a field of AI. Machine learning enables computers to learn.",
            "The algorithm works by processing data. Therefore, it can make predictions. However, it requires training.",
            "",
        ]
        
        for text in test_texts:
            key_sentence = conversation_manager._extract_key_sentence(text)
            
            if text:
                assert len(key_sentence) > 0
                assert key_sentence in text or key_sentence == text[:100]
            else:
                assert len(key_sentence) <= 100
    
    def test_enhanced_conversation_summarization(self, conversation_manager, sample_messages):
        """Test enhanced conversation summarization."""
        # Create conversation and add messages
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        for message in sample_messages:
            conversation_manager.add_message(conversation_id, message)
        
        # Generate summary
        summary = conversation_manager.summarize_conversation(conversation_id)
        
        assert len(summary) > 0
        assert "Topics discussed:" in summary or "Q1:" in summary
        
        # Should contain relevant terms from conversation
        summary_lower = summary.lower()
        expected_terms = ["machine", "learning", "neural"]
        assert any(term in summary_lower for term in expected_terms)
    
    def test_context_with_summarization_enabled(self, conversation_manager, sample_messages):
        """Test context extraction with summarization enabled."""
        # Enable summarization
        conversation_manager.enable_summarization = True
        
        # Create conversation with many messages
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        for message in sample_messages:
            conversation_manager.add_message(conversation_id, message)
        
        # Get context with small token limit to trigger summarization
        context = conversation_manager.get_context(conversation_id, max_tokens=200)
        
        assert context.conversation_id == conversation_id
        assert len(context.recent_messages) > 0
        assert context.context_tokens <= 200
        
        # Should have generated summary
        if len(sample_messages) > 5:
            assert len(context.summary) > 0
    
    def test_context_without_summarization(self, conversation_manager, sample_messages):
        """Test context extraction with summarization disabled."""
        # Disable summarization
        conversation_manager.enable_summarization = False
        
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        for message in sample_messages:
            conversation_manager.add_message(conversation_id, message)
        
        # Get context with small token limit
        context = conversation_manager.get_context(conversation_id, max_tokens=100)
        
        assert context.conversation_id == conversation_id
        assert context.context_tokens <= 100
        
        # Should still work without summarization
        assert len(context.recent_messages) > 0


if __name__ == "__main__":
    pytest.main([__file__])