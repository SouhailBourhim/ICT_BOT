"""
Structured logging configuration for the RAG system.
"""
import logging
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from config.settings import config


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


class StandardFormatter(logging.Formatter):
    """Standard formatter for human-readable logs."""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging() -> None:
    """Set up logging configuration."""
    # Create logs directory
    log_file_path = Path(config.logging.log_file)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.logging.log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    if config.logging.enable_structured_logging:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(StandardFormatter())
    
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=config.logging.log_file,
        maxBytes=config.logging.max_log_size_mb * 1024 * 1024,
        backupCount=config.logging.backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, config.logging.log_level.upper()))
    
    if config.logging.enable_structured_logging:
        file_handler.setFormatter(StructuredFormatter())
    else:
        file_handler.setFormatter(StandardFormatter())
    
    root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str, **context) -> None:
    """Log message with additional context."""
    record = logger.makeRecord(
        name=logger.name,
        level=getattr(logging, level.upper()),
        fn="",
        lno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    record.extra_fields = context
    logger.handle(record)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)
    
    def log_info(self, message: str, **context) -> None:
        """Log info message with context."""
        log_with_context(self.logger, "info", message, **context)
    
    def log_warning(self, message: str, **context) -> None:
        """Log warning message with context."""
        log_with_context(self.logger, "warning", message, **context)
    
    def log_error(self, message: str, **context) -> None:
        """Log error message with context."""
        log_with_context(self.logger, "error", message, **context)
    
    def log_debug(self, message: str, **context) -> None:
        """Log debug message with context."""
        log_with_context(self.logger, "debug", message, **context)


# Initialize logging on import
setup_logging()