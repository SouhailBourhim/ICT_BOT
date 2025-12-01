"""
Configuration settings with environment variable support.
"""
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent / '.env')


@dataclass
class DatabaseConfig:
    """Database configuration."""
    chroma_path: str = field(default_factory=lambda: os.getenv("CHROMA_PATH", "chroma"))
    metadata_db_path: str = field(default_factory=lambda: os.getenv("METADATA_DB_PATH", "data/metadata.db"))
    conversation_db_path: str = field(default_factory=lambda: os.getenv("CONVERSATION_DB_PATH", "data/conversations.db"))
    analytics_db_path: str = field(default_factory=lambda: os.getenv("ANALYTICS_DB_PATH", "data/analytics.db"))


@dataclass
class ModelConfig:
    """Model configuration."""
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "llama3"))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_TOKENS", "4096")))
    temperature: float = field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.1")))


@dataclass
class RetrievalConfig:
    """Retrieval configuration."""
    default_k: int = field(default_factory=lambda: int(os.getenv("DEFAULT_K", "5")))
    max_k: int = field(default_factory=lambda: int(os.getenv("MAX_K", "20")))
    similarity_threshold: float = field(default_factory=lambda: float(os.getenv("SIMILARITY_THRESHOLD", "0.7")))
    hybrid_alpha: float = field(default_factory=lambda: float(os.getenv("HYBRID_ALPHA", "0.5")))  # Balance between semantic and keyword
    rerank_top_k: int = field(default_factory=lambda: int(os.getenv("RERANK_TOP_K", "10")))


@dataclass
class ProcessingConfig:
    """Document processing configuration."""
    min_chunk_size: int = field(default_factory=lambda: int(os.getenv("MIN_CHUNK_SIZE", "500")))
    max_chunk_size: int = field(default_factory=lambda: int(os.getenv("MAX_CHUNK_SIZE", "2000")))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200")))
    supported_formats: list = field(default_factory=lambda: ["pdf", "txt", "docx", "md"])
    batch_size: int = field(default_factory=lambda: int(os.getenv("BATCH_SIZE", "10")))


@dataclass
class ConversationConfig:
    """Conversation management configuration."""
    max_context_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_CONTEXT_TOKENS", "2000")))
    context_window_messages: int = field(default_factory=lambda: int(os.getenv("CONTEXT_WINDOW_MESSAGES", "10")))
    conversation_timeout_hours: int = field(default_factory=lambda: int(os.getenv("CONVERSATION_TIMEOUT_HOURS", "24")))
    enable_summarization: bool = field(default_factory=lambda: os.getenv("ENABLE_SUMMARIZATION", "true").lower() == "true")


@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: str = field(default_factory=lambda: os.getenv("LOG_FILE", "logs/rag_system.log"))
    max_log_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_LOG_SIZE_MB", "100")))
    backup_count: int = field(default_factory=lambda: int(os.getenv("BACKUP_COUNT", "5")))
    enable_structured_logging: bool = field(default_factory=lambda: os.getenv("ENABLE_STRUCTURED_LOGGING", "true").lower() == "true")


@dataclass
class PerformanceConfig:
    """Performance and monitoring configuration."""
    enable_caching: bool = field(default_factory=lambda: os.getenv("ENABLE_CACHING", "true").lower() == "true")
    cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "3600")))
    max_concurrent_requests: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_REQUESTS", "10")))
    request_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")))
    enable_metrics: bool = field(default_factory=lambda: os.getenv("ENABLE_METRICS", "true").lower() == "true")


@dataclass
class UIConfig:
    """User interface configuration."""
    page_title: str = field(default_factory=lambda: os.getenv("PAGE_TITLE", "Assistant Smart ICT"))
    page_icon: str = field(default_factory=lambda: os.getenv("PAGE_ICON", "🎓"))
    enable_auto_complete: bool = field(default_factory=lambda: os.getenv("ENABLE_AUTO_COMPLETE", "true").lower() == "true")
    max_response_length: int = field(default_factory=lambda: int(os.getenv("MAX_RESPONSE_LENGTH", "5000")))
    enable_citations: bool = field(default_factory=lambda: os.getenv("ENABLE_CITATIONS", "true").lower() == "true")


@dataclass
class SystemConfig:
    """Main system configuration."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    conversation: ConversationConfig = field(default_factory=ConversationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    def __post_init__(self):
        """Create necessary directories."""
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            Path(self.database.chroma_path).parent,
            Path(self.database.metadata_db_path).parent,
            Path(self.database.conversation_db_path).parent,
            Path(self.database.analytics_db_path).parent,
            Path(self.logging.log_file).parent,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        try:
            # Validate chunk sizes
            if self.processing.min_chunk_size >= self.processing.max_chunk_size:
                raise ValueError("min_chunk_size must be less than max_chunk_size")
            
            # Validate retrieval parameters
            if self.retrieval.default_k > self.retrieval.max_k:
                raise ValueError("default_k must be less than or equal to max_k")
            
            # Validate similarity threshold
            if not 0.0 <= self.retrieval.similarity_threshold <= 1.0:
                raise ValueError("similarity_threshold must be between 0.0 and 1.0")
            
            # Validate hybrid alpha
            if not 0.0 <= self.retrieval.hybrid_alpha <= 1.0:
                raise ValueError("hybrid_alpha must be between 0.0 and 1.0")
            
            # Validate temperature
            if not 0.0 <= self.model.temperature <= 2.0:
                raise ValueError("temperature must be between 0.0 and 2.0")
            
            return True
            
        except ValueError as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "database": self.database.__dict__,
            "model": self.model.__dict__,
            "retrieval": self.retrieval.__dict__,
            "processing": self.processing.__dict__,
            "conversation": self.conversation.__dict__,
            "logging": self.logging.__dict__,
            "performance": self.performance.__dict__,
            "ui": self.ui.__dict__,
        }


# Global configuration instance
config = SystemConfig()

# Validate configuration on import
try:
    config.validate()
except ValueError as e:
    print(f"Warning: {e}")


def get_settings() -> SystemConfig:
    """Get the global configuration instance."""
    return config