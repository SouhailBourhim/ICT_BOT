"""
Advanced follow-up question detection using linguistic patterns and embeddings.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from models.base import Message, ConversationContext
from config.settings import config


logger = logging.getLogger(__name__)


class FollowUpDetector:
    """Advanced follow-up question detection system."""
    
    def __init__(self):
        """Initialize follow-up detector with patterns and configurations."""
        self.similarity_threshold = 0.7
        self.context_window_minutes = 30  # Consider messages within 30 minutes
        self.max_context_messages = 5
        
        # Linguistic patterns for follow-up detection
        self._init_linguistic_patterns()
    
    def _init_linguistic_patterns(self) -> None:
        """Initialize linguistic patterns for follow-up detection."""
        # Direct follow-up indicators
        self.direct_followup_patterns = [
            r'\b(what about|how about|and|also|additionally|furthermore|moreover)\b',
            r'\b(can you explain|tell me more|elaborate on|expand on)\b',
            r'\b(what if|suppose|assuming|given that|considering)\b',
            r'\b(in addition|besides|apart from|other than)\b',
            r'\b(similarly|likewise|in the same way|on the other hand)\b'
        ]
        
        # Pronoun and reference patterns
        self.reference_patterns = [
            r'\b(it|this|that|they|them|these|those)\b',
            r'\b(he|she|his|her|its|their)\b',
            r'\b(such|said|mentioned|above|previous)\b'
        ]
        
        # Question continuation patterns
        self.continuation_patterns = [
            r'\b(but|however|though|although|yet)\b',
            r'\b(then|next|after|following|subsequently)\b',
            r'\b(why|how|when|where|which|who)\b'
        ]
        
        # Comparative patterns
        self.comparative_patterns = [
            r'\b(compared to|versus|vs|against|rather than)\b',
            r'\b(better|worse|different|similar|same|like)\b',
            r'\b(instead|alternatively|or|either)\b'
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = {
            'direct': [re.compile(pattern, re.IGNORECASE) for pattern in self.direct_followup_patterns],
            'reference': [re.compile(pattern, re.IGNORECASE) for pattern in self.reference_patterns],
            'continuation': [re.compile(pattern, re.IGNORECASE) for pattern in self.continuation_patterns],
            'comparative': [re.compile(pattern, re.IGNORECASE) for pattern in self.comparative_patterns]
        }
    
    def detect_followup(self, current_query: str, context: ConversationContext, 
                       use_embeddings: bool = False) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Detect if current query is a follow-up question.
        
        Returns:
            Tuple of (is_followup, confidence_score, detection_details)
        """
        if not context.recent_messages:
            return False, 0.0, {"reason": "no_context"}
        
        # Get relevant context messages
        relevant_messages = self._get_relevant_context_messages(
            context.recent_messages, current_query
        )
        
        if not relevant_messages:
            return False, 0.0, {"reason": "no_relevant_context"}
        
        # Perform linguistic pattern analysis
        linguistic_score, linguistic_details = self._analyze_linguistic_patterns(
            current_query, relevant_messages
        )
        
        # Perform contextual analysis
        contextual_score, contextual_details = self._analyze_contextual_features(
            current_query, relevant_messages
        )
        
        # Perform embedding-based similarity if requested
        embedding_score = 0.0
        embedding_details = {}
        if use_embeddings:
            embedding_score, embedding_details = self._analyze_embedding_similarity(
                current_query, relevant_messages
            )
        
        # Combine scores with weights
        weights = {
            'linguistic': 0.4,
            'contextual': 0.4,
            'embedding': 0.2 if use_embeddings else 0.0
        }
        
        # Adjust weights if not using embeddings
        if not use_embeddings:
            weights['linguistic'] = 0.5
            weights['contextual'] = 0.5
        
        combined_score = (
            linguistic_score * weights['linguistic'] +
            contextual_score * weights['contextual'] +
            embedding_score * weights['embedding']
        )
        
        # Determine if it's a follow-up based on threshold
        is_followup = combined_score >= 0.5
        
        # Compile detection details
        detection_details = {
            'linguistic_score': linguistic_score,
            'contextual_score': contextual_score,
            'embedding_score': embedding_score,
            'combined_score': combined_score,
            'linguistic_details': linguistic_details,
            'contextual_details': contextual_details,
            'embedding_details': embedding_details,
            'relevant_messages_count': len(relevant_messages)
        }
        
        logger.debug(f"Follow-up detection for '{current_query[:50]}...': "
                    f"is_followup={is_followup}, score={combined_score:.3f}")
        
        return is_followup, combined_score, detection_details
    
    def _get_relevant_context_messages(self, messages: List[Message], 
                                     current_query: str) -> List[Message]:
        """Get messages relevant for follow-up detection."""
        if not messages:
            return []
        
        # Filter messages by time window
        cutoff_time = datetime.now() - timedelta(minutes=self.context_window_minutes)
        recent_messages = [
            msg for msg in messages 
            if msg.timestamp >= cutoff_time
        ]
        
        # Limit to max context messages
        relevant_messages = recent_messages[-self.max_context_messages:]
        
        # Prioritize user messages for context
        user_messages = [msg for msg in relevant_messages if msg.role == "user"]
        assistant_messages = [msg for msg in relevant_messages if msg.role == "assistant"]
        
        # Include last few user messages and corresponding assistant responses
        context_messages = []
        if user_messages:
            # Add last user message and its response
            last_user_msg = user_messages[-1]
            context_messages.append(last_user_msg)
            
            # Find corresponding assistant response
            for msg in assistant_messages:
                if msg.timestamp > last_user_msg.timestamp:
                    context_messages.append(msg)
                    break
        
        return context_messages
    
    def _analyze_linguistic_patterns(self, query: str, 
                                   context_messages: List[Message]) -> Tuple[float, Dict[str, Any]]:
        """Analyze linguistic patterns for follow-up indicators."""
        query_lower = query.lower()
        
        # Check for different pattern types
        pattern_scores = {}
        pattern_matches = {}
        
        for pattern_type, patterns in self.compiled_patterns.items():
            matches = []
            for pattern in patterns:
                found_matches = pattern.findall(query_lower)
                matches.extend(found_matches)
            
            pattern_matches[pattern_type] = matches
            # Score based on number and type of matches
            if pattern_type == 'direct':
                pattern_scores[pattern_type] = min(len(matches) * 0.4, 1.0)
            elif pattern_type == 'reference':
                pattern_scores[pattern_type] = min(len(matches) * 0.3, 0.8)
            elif pattern_type == 'continuation':
                pattern_scores[pattern_type] = min(len(matches) * 0.25, 0.6)
            elif pattern_type == 'comparative':
                pattern_scores[pattern_type] = min(len(matches) * 0.2, 0.5)
        
        # Check for question structure
        is_question = self._is_question(query)
        question_score = 0.2 if is_question else 0.0
        
        # Check for short query (often indicates follow-up)
        word_count = len(query.split())
        short_query_score = 0.3 if word_count <= 5 else 0.0
        
        # Check for incomplete sentences (often follow-ups)
        incomplete_score = 0.2 if self._is_incomplete_sentence(query) else 0.0
        
        # Combine linguistic scores
        total_pattern_score = sum(pattern_scores.values())
        linguistic_score = min(
            total_pattern_score + question_score + short_query_score + incomplete_score,
            1.0
        )
        
        details = {
            'pattern_scores': pattern_scores,
            'pattern_matches': pattern_matches,
            'is_question': is_question,
            'word_count': word_count,
            'is_short_query': word_count <= 5,
            'is_incomplete': self._is_incomplete_sentence(query),
            'total_score': linguistic_score
        }
        
        return linguistic_score, details
    
    def _analyze_contextual_features(self, query: str, 
                                   context_messages: List[Message]) -> Tuple[float, Dict[str, Any]]:
        """Analyze contextual features for follow-up detection."""
        if not context_messages:
            return 0.0, {}
        
        # Get last user message for comparison
        last_user_message = None
        for msg in reversed(context_messages):
            if msg.role == "user":
                last_user_message = msg
                break
        
        if not last_user_message:
            return 0.0, {"reason": "no_previous_user_message"}
        
        # Analyze topic continuity
        topic_score = self._calculate_topic_continuity(query, last_user_message.content)
        
        # Analyze temporal proximity
        time_diff = datetime.now() - last_user_message.timestamp
        temporal_score = self._calculate_temporal_score(time_diff)
        
        # Analyze query complexity relative to previous
        complexity_score = self._calculate_complexity_relationship(
            query, last_user_message.content
        )
        
        # Check for entity references
        entity_score = self._calculate_entity_reference_score(
            query, context_messages
        )
        
        # Combine contextual scores
        contextual_score = (
            topic_score * 0.4 +
            temporal_score * 0.2 +
            complexity_score * 0.2 +
            entity_score * 0.2
        )
        
        details = {
            'topic_continuity_score': topic_score,
            'temporal_score': temporal_score,
            'complexity_score': complexity_score,
            'entity_reference_score': entity_score,
            'time_since_last_message': time_diff.total_seconds(),
            'last_user_message_preview': last_user_message.content[:100]
        }
        
        return contextual_score, details
    
    def _analyze_embedding_similarity(self, query: str, 
                                    context_messages: List[Message]) -> Tuple[float, Dict[str, Any]]:
        """Analyze semantic similarity using embeddings (placeholder for now)."""
        # This would integrate with an embedding model in production
        # For now, return a simple lexical similarity score
        
        if not context_messages:
            return 0.0, {}
        
        # Get text from context messages
        context_text = " ".join([msg.content for msg in context_messages if msg.role == "user"])
        
        # Simple lexical similarity (would be replaced with actual embeddings)
        similarity_score = self._calculate_lexical_similarity(query, context_text)
        
        details = {
            'method': 'lexical_similarity',  # Would be 'embedding_similarity' in production
            'similarity_score': similarity_score,
            'context_length': len(context_text)
        }
        
        return similarity_score, details
    
    def _is_question(self, text: str) -> bool:
        """Check if text is a question."""
        # Primary indicator: question mark
        if '?' in text:
            return True
        
        # Question word indicators at the beginning
        question_starters = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'could', 'would', 'should', 'do', 'does', 'did', 'will', 'is', 'are', 'was', 'were']
        text_lower = text.lower().strip()
        
        # Check if starts with question word
        for starter in question_starters:
            if text_lower.startswith(starter + ' '):
                return True
        
        return False
    
    def _is_incomplete_sentence(self, text: str) -> bool:
        """Check if sentence appears incomplete (common in follow-ups)."""
        text = text.strip()
        
        # Check for incomplete patterns at the beginning
        incomplete_patterns = [
            r'^(and|but|or|so|then|also|additionally)\b',
            r'^(what about|how about)\b',
        ]
        
        for pattern in incomplete_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Check if it doesn't end with proper punctuation
        if not text.endswith(('.', '?', '!')):
            # But exclude complete questions that just don't have punctuation
            if not self._is_question(text):
                return True
            # Special case: questions that trail off (like "What if we use")
            elif len(text.split()) <= 5 and any(word in text.lower() for word in ['what if', 'suppose', 'assuming']):
                return True
        
        return False
    
    def _calculate_topic_continuity(self, current_query: str, previous_query: str) -> float:
        """Calculate topic continuity between queries."""
        # Extract keywords from both queries
        current_keywords = self._extract_keywords(current_query)
        previous_keywords = self._extract_keywords(previous_query)
        
        if not current_keywords or not previous_keywords:
            return 0.0
        
        # Calculate overlap
        common_keywords = set(current_keywords) & set(previous_keywords)
        total_keywords = set(current_keywords) | set(previous_keywords)
        
        if not total_keywords:
            return 0.0
        
        overlap_ratio = len(common_keywords) / len(total_keywords)
        return min(overlap_ratio * 2, 1.0)  # Boost the score
    
    def _calculate_temporal_score(self, time_diff: timedelta) -> float:
        """Calculate temporal proximity score."""
        minutes = time_diff.total_seconds() / 60
        
        if minutes <= 1:
            return 1.0
        elif minutes <= 5:
            return 0.8
        elif minutes <= 15:
            return 0.6
        elif minutes <= 30:
            return 0.4
        else:
            return 0.2
    
    def _calculate_complexity_relationship(self, current_query: str, previous_query: str) -> float:
        """Calculate relationship between query complexities."""
        current_complexity = len(current_query.split())
        previous_complexity = len(previous_query.split())
        
        # Follow-ups are often shorter or similar length
        if current_complexity <= previous_complexity:
            return 0.6
        elif current_complexity <= previous_complexity * 1.5:
            return 0.4
        else:
            return 0.2
    
    def _calculate_entity_reference_score(self, query: str, context_messages: List[Message]) -> float:
        """Calculate score based on entity references."""
        # Extract potential entities from context
        context_text = " ".join([msg.content for msg in context_messages])
        context_entities = self._extract_entities(context_text)
        
        # Check if current query references these entities
        query_lower = query.lower()
        referenced_entities = 0
        
        for entity in context_entities:
            if entity.lower() in query_lower:
                referenced_entities += 1
        
        if not context_entities:
            return 0.0
        
        return min(referenced_entities / len(context_entities), 1.0)
    
    def _calculate_lexical_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple lexical similarity between texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Comprehensive stop words list
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'a', 'an',
            'what', 'how', 'why', 'when', 'where', 'who', 'which', 'that', 'this', 'it',
            'they', 'them', 'their', 'there', 'then', 'than', 'from', 'up', 'out', 'if',
            'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'among', 'under', 'over'
        }
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        return keywords
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract potential entities from text."""
        # Simple entity extraction (would use NER in production)
        # Look for capitalized words and technical terms
        entities = []
        
        # Find capitalized words (potential proper nouns)
        capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities.extend(capitalized_words)
        
        # Find technical terms (words with specific patterns)
        technical_patterns = [
            r'\b\w*learning\w*\b',
            r'\b\w*network\w*\b',
            r'\b\w*algorithm\w*\b',
            r'\b\w*model\w*\b',
            r'\b\w*system\w*\b'
        ]
        
        for pattern in technical_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)
        
        return list(set(entities))  # Remove duplicates
    
    def get_followup_context_integration(self, current_query: str, 
                                       context: ConversationContext) -> Dict[str, Any]:
        """Get context integration suggestions for follow-up queries."""
        is_followup, confidence, details = self.detect_followup(current_query, context)
        
        if not is_followup:
            return {
                'is_followup': False,
                'enhanced_query': current_query,
                'context_additions': []
            }
        
        # Extract relevant context for query enhancement
        context_additions = []
        
        # Add topic context from recent messages
        if context.relevant_topics:
            context_additions.append(f"Related topics: {', '.join(context.relevant_topics[:3])}")
        
        # Add previous query context if available
        if context.recent_messages:
            last_user_msg = None
            for msg in reversed(context.recent_messages):
                if msg.role == "user":
                    last_user_msg = msg
                    break
            
            if last_user_msg:
                context_additions.append(f"Previous question: {last_user_msg.content[:100]}")
        
        # Create enhanced query with context
        enhanced_query = current_query
        if context_additions:
            context_str = " | ".join(context_additions)
            enhanced_query = f"{current_query} [Context: {context_str}]"
        
        return {
            'is_followup': True,
            'confidence': confidence,
            'enhanced_query': enhanced_query,
            'context_additions': context_additions,
            'detection_details': details
        }