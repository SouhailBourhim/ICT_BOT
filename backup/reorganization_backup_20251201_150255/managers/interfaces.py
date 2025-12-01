"""
Abstract interfaces for management components.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from models.base import (
    Conversation, Message, ConversationContext, Response, 
    RetrievalResult, EnhancedQuery
)


class ConversationManagerInterface(ABC):
    """Abstract interface for conversation management."""
    
    @abstractmethod
    def start_conversation(self, user_id: str) -> str:
        """Start a new conversation and return conversation_id."""
        pass
    
    @abstractmethod
    def add_message(self, conversation_id: str, message: Message) -> None:
        """Add a message to conversation."""
        pass
    
    @abstractmethod
    def get_context(self, conversation_id: str, max_tokens: int) -> ConversationContext:
        """Get conversation context."""
        pass
    
    @abstractmethod
    def detect_followup(self, current_query: str, context: ConversationContext) -> bool:
        """Detect if current query is a follow-up."""
        pass
    
    @abstractmethod
    def summarize_conversation(self, conversation_id: str) -> str:
        """Summarize conversation for context management."""
        pass


class ResponseManagerInterface(ABC):
    """Abstract interface for response management."""
    
    @abstractmethod
    def generate_response(self, query: str, context: List[RetrievalResult], 
                         conversation: Optional[ConversationContext]) -> Response:
        """Generate response from query and context."""
        pass
    
    @abstractmethod
    def add_citations(self, response: str, sources: List[RetrievalResult]) -> str:
        """Add citations to response."""
        pass
    
    @abstractmethod
    def assess_confidence(self, response: str, sources: List[RetrievalResult]) -> float:
        """Assess confidence in response."""
        pass
    
    @abstractmethod
    def synthesize_sources(self, sources: List[RetrievalResult]) -> str:
        """Synthesize information from multiple sources."""
        pass


class AnalyticsManagerInterface(ABC):
    """Abstract interface for analytics management."""
    
    @abstractmethod
    def log_query(self, query: str, response: Response, metadata: Dict[str, Any]) -> None:
        """Log query and response for analytics."""
        pass
    
    @abstractmethod
    def track_performance(self, operation: str, duration: float, metadata: Dict[str, Any]) -> None:
        """Track performance metrics."""
        pass
    
    @abstractmethod
    def collect_feedback(self, conversation_id: str, message_id: str, 
                        feedback: Dict[str, Any]) -> None:
        """Collect user feedback."""
        pass
    
    @abstractmethod
    def generate_analytics_report(self, time_period: str) -> Dict[str, Any]:
        """Generate analytics report."""
        pass


class ErrorHandlerInterface(ABC):
    """Abstract interface for error handling."""
    
    @abstractmethod
    def handle_service_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle service errors with recovery strategies."""
        pass
    
    @abstractmethod
    def implement_retry_logic(self, operation: callable, max_retries: int = 3) -> Any:
        """Implement retry logic with exponential backoff."""
        pass
    
    @abstractmethod
    def graceful_degradation(self, feature: str, fallback: callable) -> Any:
        """Implement graceful degradation for features."""
        pass
    
    @abstractmethod
    def log_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Log error with context."""
        pass


class ConfigurationManagerInterface(ABC):
    """Abstract interface for configuration management."""
    
    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        pass
    
    @abstractmethod
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        pass
    
    @abstractmethod
    def load_config_from_file(self, file_path: str) -> None:
        """Load configuration from file."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate configuration."""
        pass