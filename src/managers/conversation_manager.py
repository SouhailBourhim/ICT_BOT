"""
Conversation management system for maintaining conversation history and context.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import sqlite3
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.models.base import (
    Conversation, Message, ConversationContext, QueryIntent
)
from .interfaces import ConversationManagerInterface
from .followup_detector import FollowUpDetector
from config.settings import config


logger = logging.getLogger(__name__)


class ConversationManager(ConversationManagerInterface):
    """Manages conversation storage, retrieval, and context management."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize conversation manager with database connection."""
        self.db_path = db_path or config.database.conversation_db_path
        self.max_context_tokens = config.conversation.max_context_tokens
        self.context_window_messages = config.conversation.context_window_messages
        self.conversation_timeout_hours = config.conversation.conversation_timeout_hours
        self.enable_summarization = config.conversation.enable_summarization
        
        # Initialize follow-up detector
        self.followup_detector = FollowUpDetector()
        
        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with conversation schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create conversations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        conversation_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        context_summary TEXT,
                        metadata TEXT,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
                
                # Create messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        sources TEXT,
                        confidence REAL,
                        metadata TEXT,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
                    ON conversations (user_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_updated_at 
                    ON conversations (updated_at)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
                    ON messages (conversation_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                    ON messages (timestamp)
                """)
                
                conn.commit()
                logger.info("Conversation database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize conversation database: {e}")
            raise
    
    def start_conversation(self, user_id: str) -> str:
        """Start a new conversation and return conversation_id."""
        conversation_id = str(uuid.uuid4())
        now = datetime.now()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO conversations 
                    (conversation_id, user_id, created_at, updated_at, context_summary, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    conversation_id,
                    user_id,
                    now,
                    now,
                    "",
                    json.dumps({})
                ))
                conn.commit()
                
            logger.info(f"Started new conversation {conversation_id} for user {user_id}")
            return conversation_id
            
        except sqlite3.Error as e:
            logger.error(f"Failed to start conversation: {e}")
            raise
    
    def add_message(self, conversation_id: str, message: Message) -> None:
        """Add a message to conversation."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert message
                cursor.execute("""
                    INSERT INTO messages 
                    (message_id, conversation_id, role, content, timestamp, sources, confidence, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.message_id,
                    conversation_id,
                    message.role,
                    message.content,
                    message.timestamp,
                    json.dumps(message.sources),
                    message.confidence,
                    json.dumps({})
                ))
                
                # Update conversation timestamp
                cursor.execute("""
                    UPDATE conversations 
                    SET updated_at = ? 
                    WHERE conversation_id = ?
                """, (datetime.now(), conversation_id))
                
                conn.commit()
                
            logger.debug(f"Added message {message.message_id} to conversation {conversation_id}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to add message to conversation: {e}")
            raise
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get complete conversation by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get conversation metadata
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE conversation_id = ? AND is_active = 1
                """, (conversation_id,))
                
                conv_row = cursor.fetchone()
                if not conv_row:
                    return None
                
                # Get messages
                cursor.execute("""
                    SELECT * FROM messages 
                    WHERE conversation_id = ? 
                    ORDER BY timestamp ASC
                """, (conversation_id,))
                
                message_rows = cursor.fetchall()
                
                # Build message objects
                messages = []
                for row in message_rows:
                    message = Message(
                        message_id=row['message_id'],
                        role=row['role'],
                        content=row['content'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        sources=json.loads(row['sources'] or '[]'),
                        confidence=row['confidence'] or 0.0
                    )
                    messages.append(message)
                
                # Build conversation object
                conversation = Conversation(
                    conversation_id=conv_row['conversation_id'],
                    user_id=conv_row['user_id'],
                    created_at=datetime.fromisoformat(conv_row['created_at']),
                    updated_at=datetime.fromisoformat(conv_row['updated_at']),
                    messages=messages,
                    context_summary=conv_row['context_summary'] or ""
                )
                
                return conversation
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            raise
    
    def get_context(self, conversation_id: str, max_tokens: int) -> ConversationContext:
        """Get conversation context for query processing with advanced window management."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return ConversationContext(
                conversation_id=conversation_id,
                recent_messages=[],
                summary="",
                relevant_topics=[],
                context_tokens=0
            )
        
        # Apply sliding window context extraction
        recent_messages, context_tokens = self._extract_sliding_window_context(
            conversation.messages, max_tokens
        )
        
        # Score message relevance and select most relevant ones if needed
        if len(recent_messages) > self.context_window_messages:
            recent_messages = self._select_relevant_messages(
                recent_messages, self.context_window_messages
            )
            context_tokens = sum(len(msg.content) // 4 for msg in recent_messages)
        
        # Extract relevant topics from recent messages
        relevant_topics = self._extract_topics(recent_messages)
        
        # Get or generate conversation summary
        summary = conversation.context_summary
        if not summary and len(conversation.messages) > 5:
            summary = self.summarize_conversation(conversation_id)
        
        return ConversationContext(
            conversation_id=conversation_id,
            recent_messages=recent_messages,
            summary=summary,
            relevant_topics=relevant_topics,
            context_tokens=context_tokens
        )
    
    def _extract_sliding_window_context(self, messages: List[Message], max_tokens: int) -> tuple[List[Message], int]:
        """Extract messages using sliding window approach with token management."""
        if not messages:
            return [], 0
        
        # Start from most recent messages and work backwards
        selected_messages = []
        current_tokens = 0
        
        # Reserve tokens for summary if summarization is enabled
        available_tokens = max_tokens
        if self.enable_summarization and len(messages) > self.context_window_messages:
            available_tokens = max_tokens * 0.7  # Reserve 30% for summary
        
        for message in reversed(messages):
            msg_tokens = self._estimate_tokens(message.content)
            
            if current_tokens + msg_tokens <= available_tokens:
                selected_messages.insert(0, message)
                current_tokens += msg_tokens
            else:
                # Try to fit partial message if it's the first one
                if not selected_messages and msg_tokens > available_tokens:
                    # Truncate message to fit
                    truncated_content = self._truncate_to_tokens(message.content, int(available_tokens))
                    truncated_message = Message(
                        message_id=message.message_id,
                        role=message.role,
                        content=truncated_content,
                        timestamp=message.timestamp,
                        sources=message.sources,
                        confidence=message.confidence
                    )
                    selected_messages.insert(0, truncated_message)
                    current_tokens = self._estimate_tokens(truncated_content)
                break
        
        return selected_messages, current_tokens
    
    def _select_relevant_messages(self, messages: List[Message], max_messages: int) -> List[Message]:
        """Select most relevant messages based on relevance scoring."""
        if len(messages) <= max_messages:
            return messages
        
        # Score messages for relevance
        scored_messages = []
        for i, message in enumerate(messages):
            relevance_score = self._calculate_message_relevance(message, i, len(messages))
            scored_messages.append((message, relevance_score))
        
        # Sort by relevance score (descending) and recency
        scored_messages.sort(key=lambda x: (x[1], x[0].timestamp), reverse=True)
        
        # Select top messages but ensure we keep the most recent ones
        selected = []
        recent_count = min(3, max_messages // 2)  # Keep at least 3 most recent
        
        # Add most recent messages first
        for message, _ in scored_messages[-recent_count:]:
            selected.append(message)
        
        # Add highest scoring messages from the rest
        remaining_slots = max_messages - len(selected)
        for message, _ in scored_messages[:-recent_count][:remaining_slots]:
            if message not in selected:
                selected.append(message)
        
        # Sort by timestamp to maintain chronological order
        selected.sort(key=lambda x: x.timestamp)
        return selected
    
    def _calculate_message_relevance(self, message: Message, position: int, total_messages: int) -> float:
        """Calculate relevance score for a message."""
        # Base score factors
        recency_score = position / total_messages  # More recent = higher score
        length_score = min(len(message.content) / 500, 1.0)  # Longer messages up to 500 chars
        
        # Role-based scoring
        role_score = 1.0 if message.role == "user" else 0.8  # Prioritize user messages
        
        # Content-based scoring
        content_score = 0.5
        if message.sources:  # Messages with sources are more valuable
            content_score += 0.3
        if message.confidence > 0.8:  # High confidence messages
            content_score += 0.2
        
        # Question detection (user queries are important)
        if message.role == "user" and any(word in message.content.lower() 
                                        for word in ["what", "how", "why", "when", "where", "?"]):
            content_score += 0.3
        
        # Combine scores
        total_score = (recency_score * 0.4 + 
                      length_score * 0.2 + 
                      role_score * 0.2 + 
                      content_score * 0.2)
        
        return total_score
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # More accurate estimation: ~4 characters per token for English
        # Account for punctuation and spaces
        return max(1, len(text.split()) * 1.3)  # Words * 1.3 for subword tokens
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximately fit within token limit."""
        words = text.split()
        estimated_tokens = 0
        truncated_words = []
        
        for word in words:
            word_tokens = len(word) / 4 + 0.3  # Rough estimation per word
            if estimated_tokens + word_tokens <= max_tokens:
                truncated_words.append(word)
                estimated_tokens += word_tokens
            else:
                break
        
        truncated_text = " ".join(truncated_words)
        if len(truncated_words) < len(words):
            truncated_text += "..."
        
        return truncated_text
    
    def detect_followup(self, current_query: str, context: ConversationContext) -> bool:
        """Detect if current query is a follow-up question using advanced detection."""
        is_followup, confidence, details = self.followup_detector.detect_followup(
            current_query, context, use_embeddings=False
        )
        
        logger.debug(f"Follow-up detection for '{current_query}': {is_followup} (confidence: {confidence:.3f})")
        return is_followup
    
    def detect_followup_detailed(self, current_query: str, context: ConversationContext, 
                               use_embeddings: bool = False) -> tuple[bool, float, Dict[str, Any]]:
        """Detect follow-up with detailed analysis and confidence score."""
        return self.followup_detector.detect_followup(current_query, context, use_embeddings)
    
    def get_followup_context_integration(self, current_query: str, 
                                       context: ConversationContext) -> Dict[str, Any]:
        """Get enhanced query context for follow-up questions."""
        return self.followup_detector.get_followup_context_integration(current_query, context)
    
    def summarize_conversation(self, conversation_id: str) -> str:
        """Generate comprehensive conversation summary for long sessions."""
        conversation = self.get_conversation(conversation_id)
        if not conversation or not conversation.messages:
            return ""
        
        # Enhanced extractive summarization with topic clustering
        summary = self._generate_extractive_summary(conversation.messages)
        
        # Update conversation summary in database
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE conversations 
                    SET context_summary = ? 
                    WHERE conversation_id = ?
                """, (summary, conversation_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update conversation summary: {e}")
        
        return summary
    
    def _generate_extractive_summary(self, messages: List[Message]) -> str:
        """Generate extractive summary from conversation messages."""
        if not messages:
            return ""
        
        # Group messages into conversation turns
        turns = self._group_into_turns(messages)
        
        # Extract key topics and themes
        topics = self._extract_conversation_topics(messages)
        
        # Select most important turns for summary
        important_turns = self._select_important_turns(turns, max_turns=5)
        
        # Generate structured summary
        summary_parts = []
        
        # Add topic overview if available
        if topics:
            topic_summary = f"Topics discussed: {', '.join(topics[:5])}"
            summary_parts.append(topic_summary)
        
        # Add key conversation turns
        for i, turn in enumerate(important_turns):
            user_msg = turn.get('user', '')
            assistant_msg = turn.get('assistant', '')
            
            if user_msg and assistant_msg:
                # Truncate for summary
                user_summary = self._extract_key_sentence(user_msg)[:150]
                assistant_summary = self._extract_key_sentence(assistant_msg)[:200]
                
                turn_summary = f"Q{i+1}: {user_summary} → A{i+1}: {assistant_summary}"
                summary_parts.append(turn_summary)
        
        return " | ".join(summary_parts)
    
    def _group_into_turns(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Group messages into conversation turns (user query + assistant response)."""
        turns = []
        current_turn = {}
        
        for message in messages:
            if message.role == "user":
                # Start new turn if we have a complete previous turn
                if current_turn.get('user') and current_turn.get('assistant'):
                    turns.append(current_turn)
                    current_turn = {}
                current_turn['user'] = message.content
            elif message.role == "assistant":
                current_turn['assistant'] = message.content
        
        # Add final turn if complete
        if current_turn.get('user') and current_turn.get('assistant'):
            turns.append(current_turn)
        
        return turns
    
    def _extract_conversation_topics(self, messages: List[Message]) -> List[str]:
        """Extract main topics from conversation using enhanced keyword extraction."""
        all_text = " ".join(msg.content for msg in messages if msg.role == "user")
        words = all_text.lower().split()
        
        # Enhanced topic extraction with domain-specific terms
        technical_terms = set()
        common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'about', 'what', 'how', 'why', 'when', 'where', 'who', 'which'}
        
        # Look for technical terms and important concepts
        for word in words:
            if (len(word) > 4 and 
                word.isalpha() and 
                word not in common_words and
                not word.endswith('ing') and
                not word.endswith('ed')):
                technical_terms.add(word)
        
        # Score terms by frequency and context
        term_scores = {}
        for term in technical_terms:
            # Count occurrences
            count = all_text.lower().count(term)
            # Boost score for terms that appear with question words
            context_boost = 1.0
            if any(f"{qword} {term}" in all_text.lower() or f"{term} {qword}" in all_text.lower() 
                   for qword in ["what", "how", "why", "explain"]):
                context_boost = 1.5
            
            term_scores[term] = count * context_boost
        
        # Return top scored terms
        sorted_terms = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)
        return [term for term, score in sorted_terms[:10]]
    
    def _select_important_turns(self, turns: List[Dict[str, str]], max_turns: int = 5) -> List[Dict[str, str]]:
        """Select most important conversation turns for summary."""
        if len(turns) <= max_turns:
            return turns
        
        # Score turns by importance
        scored_turns = []
        for i, turn in enumerate(turns):
            importance_score = self._calculate_turn_importance(turn, i, len(turns))
            scored_turns.append((turn, importance_score))
        
        # Sort by importance and select top turns
        scored_turns.sort(key=lambda x: x[1], reverse=True)
        selected_turns = [turn for turn, score in scored_turns[:max_turns]]
        
        # Maintain chronological order
        turn_indices = {id(turn): i for i, turn in enumerate(turns)}
        selected_turns.sort(key=lambda x: turn_indices.get(id(x), 0))
        
        return selected_turns
    
    def _calculate_turn_importance(self, turn: Dict[str, str], position: int, total_turns: int) -> float:
        """Calculate importance score for a conversation turn."""
        user_msg = turn.get('user', '')
        assistant_msg = turn.get('assistant', '')
        
        # Base scores
        recency_score = position / total_turns  # More recent turns are more important
        length_score = min((len(user_msg) + len(assistant_msg)) / 1000, 1.0)
        
        # Question complexity (more complex questions are more important)
        question_score = 0.5
        question_words = ['what', 'how', 'why', 'explain', 'describe', 'compare', 'analyze']
        if any(word in user_msg.lower() for word in question_words):
            question_score += 0.3
        
        # Technical content (messages with technical terms are more important)
        technical_score = 0.0
        technical_indicators = ['algorithm', 'function', 'method', 'process', 'system', 'model', 'data', 'analysis']
        technical_count = sum(1 for term in technical_indicators if term in (user_msg + assistant_msg).lower())
        technical_score = min(technical_count * 0.1, 0.5)
        
        # Combine scores
        total_score = (recency_score * 0.3 + 
                      length_score * 0.2 + 
                      question_score * 0.3 + 
                      technical_score * 0.2)
        
        return total_score
    
    def _extract_key_sentence(self, text: str) -> str:
        """Extract the most informative sentence from text."""
        sentences = text.split('. ')
        if not sentences:
            return text[:100]
        
        # Score sentences by information content
        scored_sentences = []
        for sentence in sentences:
            if len(sentence.strip()) < 10:  # Skip very short sentences
                continue
            
            # Simple scoring based on length and question words
            score = len(sentence) * 0.01  # Length factor
            if any(word in sentence.lower() for word in ['what', 'how', 'why', 'explain']):
                score += 0.5  # Question bonus
            if any(word in sentence.lower() for word in ['because', 'therefore', 'however', 'moreover']):
                score += 0.3  # Explanation bonus
            
            scored_sentences.append((sentence.strip(), score))
        
        if scored_sentences:
            # Return highest scoring sentence
            best_sentence = max(scored_sentences, key=lambda x: x[1])[0]
            return best_sentence
        
        return sentences[0].strip() if sentences else text[:100]
    
    def _extract_topics(self, messages: List[Message]) -> List[str]:
        """Extract relevant topics from messages."""
        # Simple keyword extraction
        # In production, this would use more sophisticated NLP techniques
        
        all_text = " ".join(msg.content for msg in messages if msg.role == "user")
        words = all_text.lower().split()
        
        # Filter for potential topics (longer words, technical terms)
        topics = []
        for word in words:
            if (len(word) > 4 and 
                word.isalpha() and 
                word not in ['about', 'could', 'would', 'should', 'explain', 'understand']):
                topics.append(word)
        
        # Return unique topics, limited to top 10
        return list(set(topics))[:10]
    
    def get_user_conversations(self, user_id: str, limit: int = 10) -> List[Conversation]:
        """Get recent conversations for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT conversation_id FROM conversations 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY updated_at DESC 
                    LIMIT ?
                """, (user_id, limit))
                
                conversation_ids = [row['conversation_id'] for row in cursor.fetchall()]
                
                conversations = []
                for conv_id in conversation_ids:
                    conv = self.get_conversation(conv_id)
                    if conv:
                        conversations.append(conv)
                
                return conversations
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get user conversations: {e}")
            return []
    
    def cleanup_old_conversations(self) -> int:
        """Clean up old inactive conversations."""
        cutoff_time = datetime.now() - timedelta(hours=self.conversation_timeout_hours * 24)  # Keep for 24x timeout
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Mark old conversations as inactive
                cursor.execute("""
                    UPDATE conversations 
                    SET is_active = 0 
                    WHERE updated_at < ? AND is_active = 1
                """, (cutoff_time,))
                
                cleaned_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {cleaned_count} old conversations")
                return cleaned_count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup old conversations: {e}")
            return 0