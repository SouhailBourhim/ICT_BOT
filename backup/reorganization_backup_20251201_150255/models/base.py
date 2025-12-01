"""
Base data models and enums for the RAG system.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ContentType(Enum):
    """Content type classification for document chunks."""
    TEXT = "text"
    FORMULA = "formula"
    CODE = "code"
    DIAGRAM = "diagram"
    TABLE = "table"


class QueryIntent(Enum):
    """Query intent classification."""
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    CONCEPTUAL = "conceptual"
    COMPARATIVE = "comparative"
    TROUBLESHOOTING = "troubleshooting"


@dataclass
class DocumentMetadata:
    """Metadata for processed documents."""
    document_id: str
    title: str
    course_module: str
    document_type: str  # pdf, docx, txt
    creation_date: datetime
    page_count: int
    language: str
    topics: List[str]
    difficulty_level: str
    file_path: str
    file_size: int


@dataclass
class ProcessedChunk:
    """Processed document chunk with metadata."""
    chunk_id: str
    document_id: str
    content: str
    content_type: ContentType
    hierarchical_context: List[str]  # [chapter, section, subsection]
    page_number: int
    position_in_document: float  # 0.0 to 1.0
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class Message:
    """Conversation message."""
    message_id: str
    role: str  # user, assistant
    content: str
    timestamp: datetime
    sources: List[str]  # document references
    confidence: float


@dataclass
class Conversation:
    """Conversation session."""
    conversation_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message]
    context_summary: str


@dataclass
class EnhancedQuery:
    """Enhanced query with processing metadata."""
    original_query: str
    expanded_terms: List[str]
    corrected_query: str
    intent: QueryIntent
    filters: Dict[str, Any]
    context_dependent: bool


@dataclass
class RetrievalResult:
    """Result from retrieval system."""
    chunk: ProcessedChunk
    score: float
    retrieval_method: str  # semantic, keyword, hybrid
    metadata: Dict[str, Any]


@dataclass
class Response:
    """Generated response with metadata."""
    content: str
    sources: List[RetrievalResult]
    confidence: float
    citations: List[str]
    generation_metadata: Dict[str, Any]


@dataclass
class ConversationContext:
    """Context for conversation management."""
    conversation_id: str
    recent_messages: List[Message]
    summary: str
    relevant_topics: List[str]
    context_tokens: int


@dataclass
class AmbiguityReport:
    """Report on query ambiguity."""
    is_ambiguous: bool
    ambiguity_score: float
    clarification_questions: List[str]
    suggested_interpretations: List[str]


@dataclass
class FormattedChunk:
    """Chunk with preserved formatting."""
    content: str
    formatting_metadata: Dict[str, Any]
    content_type: ContentType
    preserved_elements: List[str]  # formulas, code blocks, etc.


@dataclass
class ErrorResponse:
    """Standardized error response."""
    error_type: str
    error_message: str
    error_code: str
    recovery_suggestions: List[str]
    timestamp: datetime


@dataclass
class QueryAnalytics:
    """Analytics data for query processing."""
    query_id: str
    conversation_id: str
    user_id: str
    original_query: str
    enhanced_query: str
    query_intent: QueryIntent
    timestamp: datetime
    processing_time: float
    retrieval_count: int
    response_length: int
    confidence_score: float
    sources_used: List[str]
    metadata: Dict[str, Any]


@dataclass
class ResponseQualityMetrics:
    """Metrics for response quality assessment."""
    response_id: str
    query_id: str
    relevance_score: float
    accuracy_score: float
    completeness_score: float
    citation_quality: float
    user_satisfaction: Optional[float]
    feedback_timestamp: Optional[datetime]
    metadata: Dict[str, Any]


@dataclass
class PerformanceMetrics:
    """System performance metrics."""
    metric_id: str
    operation: str
    timestamp: datetime
    duration: float
    memory_usage: float
    cpu_usage: float
    success: bool
    error_message: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class UserFeedback:
    """User feedback data."""
    feedback_id: str
    conversation_id: str
    message_id: str
    user_id: str
    rating: int  # 1-5 scale
    feedback_type: str  # helpful, accurate, complete, etc.
    comments: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any]