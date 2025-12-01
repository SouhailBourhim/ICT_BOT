"""
Unit tests for conversation management system.
"""
import pytest
import tempfile
import os
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from managers.conversation_manager import ConversationManager
from models.base import Message, Conversation, ConversationContext


class TestConversationManager:
    """Test cases for ConversationManager."""
    
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
    def sample_message(self):
        """Create sample message for testing."""
        return Message(
            message_id="msg_123",
            role="user",
            content="What is machine learning?",
            timestamp=datetime.now(),
            sources=["doc1.pdf", "doc2.pdf"],
            confidence=0.9
        )
    
    def test_database_initialization(self, conversation_manager):
        """Test database schema creation."""
        # Check if tables exist
        with sqlite3.connect(conversation_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # Check conversations table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='conversations'
            """)
            assert cursor.fetchone() is not None
            
            # Check messages table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='messages'
            """)
            assert cursor.fetchone() is not None
            
            # Check indexes
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_%'
            """)
            indexes = cursor.fetchall()
            assert len(indexes) >= 4  # Should have at least 4 indexes
    
    def test_start_conversation(self, conversation_manager):
        """Test starting a new conversation."""
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        # Verify conversation_id is returned
        assert conversation_id is not None
        assert isinstance(conversation_id, str)
        assert len(conversation_id) > 0
        
        # Verify conversation is stored in database
        conversation = conversation_manager.get_conversation(conversation_id)
        assert conversation is not None
        assert conversation.user_id == user_id
        assert conversation.conversation_id == conversation_id
        assert len(conversation.messages) == 0
    
    def test_add_message(self, conversation_manager, sample_message):
        """Test adding message to conversation."""
        # Start conversation
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        # Add message
        conversation_manager.add_message(conversation_id, sample_message)
        
        # Verify message is stored
        conversation = conversation_manager.get_conversation(conversation_id)
        assert len(conversation.messages) == 1
        
        stored_message = conversation.messages[0]
        assert stored_message.message_id == sample_message.message_id
        assert stored_message.role == sample_message.role
        assert stored_message.content == sample_message.content
        assert stored_message.sources == sample_message.sources
        assert stored_message.confidence == sample_message.confidence
    
    def test_get_conversation_nonexistent(self, conversation_manager):
        """Test getting non-existent conversation."""
        conversation = conversation_manager.get_conversation("nonexistent_id")
        assert conversation is None
    
    def test_get_context_empty_conversation(self, conversation_manager):
        """Test getting context for empty conversation."""
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        context = conversation_manager.get_context(conversation_id, max_tokens=1000)
        
        assert context.conversation_id == conversation_id
        assert len(context.recent_messages) == 0
        assert context.summary == ""
        assert context.context_tokens == 0
        assert isinstance(context.relevant_topics, list)
    
    def test_get_context_with_messages(self, conversation_manager):
        """Test getting context with messages."""
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        # Add multiple messages
        messages = [
            Message(
                message_id=f"msg_{i}",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message content {i}",
                timestamp=datetime.now(),
                sources=[],
                confidence=0.8
            )
            for i in range(5)
        ]
        
        for message in messages:
            conversation_manager.add_message(conversation_id, message)
        
        context = conversation_manager.get_context(conversation_id, max_tokens=1000)
        
        assert context.conversation_id == conversation_id
        assert len(context.recent_messages) == 5
        assert context.context_tokens > 0
    
    def test_context_window_limit(self, conversation_manager):
        """Test context window message limit."""
        # Mock configuration to test window limit
        with patch.object(conversation_manager, 'context_window_messages', 3):
            user_id = "user_123"
            conversation_id = conversation_manager.start_conversation(user_id)
            
            # Add more messages than window limit
            messages = [
                Message(
                    message_id=f"msg_{i}",
                    role="user",
                    content=f"Message {i}",
                    timestamp=datetime.now(),
                    sources=[],
                    confidence=0.8
                )
                for i in range(5)
            ]
            
            for message in messages:
                conversation_manager.add_message(conversation_id, message)
            
            context = conversation_manager.get_context(conversation_id, max_tokens=1000)
            
            # Should limit messages (may not be exactly 3 due to enhanced selection)
            assert len(context.recent_messages) <= 3
            # Should include most recent messages
            message_ids = [msg.message_id for msg in context.recent_messages]
            assert "msg_4" in message_ids  # Most recent should be included
    
    def test_detect_followup_no_context(self, conversation_manager):
        """Test follow-up detection with no context."""
        context = ConversationContext(
            conversation_id="test_id",
            recent_messages=[],
            summary="",
            relevant_topics=[],
            context_tokens=0
        )
        
        is_followup = conversation_manager.detect_followup("What is AI?", context)
        assert is_followup is False
    
    def test_detect_followup_with_patterns(self, conversation_manager):
        """Test follow-up detection with linguistic patterns."""
        # Create context with previous message
        previous_message = Message(
            message_id="msg_1",
            role="user",
            content="What is machine learning?",
            timestamp=datetime.now(),
            sources=[],
            confidence=0.8
        )
        
        context = ConversationContext(
            conversation_id="test_id",
            recent_messages=[previous_message],
            summary="",
            relevant_topics=[],
            context_tokens=50
        )
        
        # Test various follow-up patterns
        followup_queries = [
            "What about deep learning?",
            "Can you explain it more?",
            "Tell me more about this",
            "And neural networks?",
            "How about supervised learning?"
        ]
        
        for query in followup_queries:
            is_followup = conversation_manager.detect_followup(query, context)
            assert is_followup is True, f"Failed to detect follow-up: {query}"
        
        # Test non-follow-up queries
        non_followup_queries = [
            "What is the weather today?",
            "Explain quantum computing in detail",
            "I need help with my homework."
        ]
        
        for query in non_followup_queries:
            is_followup = conversation_manager.detect_followup(query, context)
            assert is_followup is False, f"Incorrectly detected follow-up: {query}"
    
    def test_detect_followup_with_pronouns(self, conversation_manager):
        """Test follow-up detection with pronouns."""
        previous_message = Message(
            message_id="msg_1",
            role="user",
            content="What is machine learning?",
            timestamp=datetime.now(),
            sources=[],
            confidence=0.8
        )
        
        context = ConversationContext(
            conversation_id="test_id",
            recent_messages=[previous_message],
            summary="",
            relevant_topics=[],
            context_tokens=50
        )
        
        # Test pronoun-based follow-ups
        pronoun_queries = [
            "It sounds complex",
            "This is interesting",
            "That makes sense"
        ]
        
        for query in pronoun_queries:
            is_followup = conversation_manager.detect_followup(query, context)
            assert is_followup is True, f"Failed to detect pronoun follow-up: {query}"
    
    def test_summarize_conversation_empty(self, conversation_manager):
        """Test conversation summarization with empty conversation."""
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        summary = conversation_manager.summarize_conversation(conversation_id)
        assert summary == ""
    
    def test_summarize_conversation_with_messages(self, conversation_manager):
        """Test conversation summarization with messages."""
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        # Add user query and assistant response
        user_message = Message(
            message_id="msg_1",
            role="user",
            content="What is machine learning and how does it work?",
            timestamp=datetime.now(),
            sources=[],
            confidence=0.8
        )
        
        assistant_message = Message(
            message_id="msg_2",
            role="assistant",
            content="Machine learning is a subset of artificial intelligence. It involves algorithms that learn patterns from data.",
            timestamp=datetime.now(),
            sources=["ml_textbook.pdf"],
            confidence=0.9
        )
        
        conversation_manager.add_message(conversation_id, user_message)
        conversation_manager.add_message(conversation_id, assistant_message)
        
        summary = conversation_manager.summarize_conversation(conversation_id)
        
        assert summary != ""
        assert "machine learning" in summary.lower()
        assert "Q1:" in summary
        assert "A1:" in summary
    
    def test_get_user_conversations(self, conversation_manager):
        """Test getting user conversations."""
        user_id = "user_123"
        
        # Create multiple conversations
        conversation_ids = []
        for i in range(3):
            conv_id = conversation_manager.start_conversation(user_id)
            conversation_ids.append(conv_id)
        
        # Get user conversations
        conversations = conversation_manager.get_user_conversations(user_id)
        
        assert len(conversations) == 3
        for conv in conversations:
            assert conv.user_id == user_id
            assert conv.conversation_id in conversation_ids
    
    def test_get_user_conversations_limit(self, conversation_manager):
        """Test getting user conversations with limit."""
        user_id = "user_123"
        
        # Create more conversations than limit
        for i in range(5):
            conversation_manager.start_conversation(user_id)
        
        # Get with limit
        conversations = conversation_manager.get_user_conversations(user_id, limit=2)
        
        assert len(conversations) == 2
    
    def test_cleanup_old_conversations(self, conversation_manager):
        """Test cleaning up old conversations."""
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        # Manually set old timestamp
        old_time = datetime.now() - timedelta(days=30)
        with sqlite3.connect(conversation_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversations 
                SET updated_at = ? 
                WHERE conversation_id = ?
            """, (old_time, conversation_id))
            conn.commit()
        
        # Run cleanup
        cleaned_count = conversation_manager.cleanup_old_conversations()
        
        assert cleaned_count == 1
        
        # Verify conversation is marked inactive
        conversation = conversation_manager.get_conversation(conversation_id)
        assert conversation is None  # Should not return inactive conversations
    
    def test_extract_topics(self, conversation_manager):
        """Test topic extraction from messages."""
        messages = [
            Message(
                message_id="msg_1",
                role="user",
                content="What is machine learning and neural networks?",
                timestamp=datetime.now(),
                sources=[],
                confidence=0.8
            ),
            Message(
                message_id="msg_2",
                role="user",
                content="How do algorithms work in artificial intelligence?",
                timestamp=datetime.now(),
                sources=[],
                confidence=0.8
            )
        ]
        
        topics = conversation_manager._extract_topics(messages)
        
        assert isinstance(topics, list)
        assert len(topics) <= 10
        # Should extract meaningful words
        topic_text = " ".join(topics).lower()
        assert any(word in topic_text for word in ["machine", "learning", "neural", "networks", "algorithms", "artificial", "intelligence"])
    
    def test_database_error_handling(self, conversation_manager):
        """Test database error handling."""
        # Close database connection to simulate error
        conversation_manager.db_path = "/invalid/path/test.db"
        
        with pytest.raises(Exception):
            conversation_manager.start_conversation("user_123")
    
    def test_token_limit_truncation(self, conversation_manager):
        """Test context truncation when token limit exceeded."""
        user_id = "user_123"
        conversation_id = conversation_manager.start_conversation(user_id)
        
        # Add messages with long content
        long_content = "This is a very long message. " * 100  # ~500 tokens
        messages = [
            Message(
                message_id=f"msg_{i}",
                role="user",
                content=long_content,
                timestamp=datetime.now(),
                sources=[],
                confidence=0.8
            )
            for i in range(10)
        ]
        
        for message in messages:
            conversation_manager.add_message(conversation_id, message)
        
        # Get context with small token limit
        context = conversation_manager.get_context(conversation_id, max_tokens=100)
        
        # Should truncate messages to fit within token limit (allow small margin for estimation)
        assert context.context_tokens <= 110  # Allow small margin for token estimation
        assert len(context.recent_messages) < 10


if __name__ == "__main__":
    pytest.main([__file__])