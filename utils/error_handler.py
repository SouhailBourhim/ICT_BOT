"""
Comprehensive error handling system for the RAG application.
Provides error classification, recovery strategies, and retry mechanisms.
"""
import logging
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union
import asyncio
from contextlib import contextmanager


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RESOURCE_ERROR = "resource_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    FAIL_FAST = "fail_fast"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    component: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ErrorInfo:
    """Structured error information."""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    original_exception: Optional[Exception] = None
    context: Optional[ErrorContext] = None
    recovery_strategy: Optional[RecoveryStrategy] = None
    retry_count: int = 0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class BaseRAGException(Exception):
    """Base exception class for RAG system errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context
        self.original_exception = original_exception
        self.timestamp = time.time()


class ServiceUnavailableError(BaseRAGException):
    """Raised when external services are unavailable."""
    
    def __init__(self, service_name: str, message: str = None, **kwargs):
        self.service_name = service_name
        message = message or f"Service '{service_name}' is unavailable"
        super().__init__(
            message,
            category=ErrorCategory.SERVICE_UNAVAILABLE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class DatabaseError(BaseRAGException):
    """Raised for database-related errors."""
    
    def __init__(self, operation: str, message: str = None, **kwargs):
        self.operation = operation
        message = message or f"Database error during '{operation}'"
        super().__init__(
            message,
            category=ErrorCategory.DATABASE_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ProcessingError(BaseRAGException):
    """Raised for document processing errors."""
    
    def __init__(self, document_id: str = None, message: str = None, **kwargs):
        self.document_id = document_id
        message = message or f"Processing error for document '{document_id}'"
        super().__init__(
            message,
            category=ErrorCategory.PROCESSING_ERROR,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ValidationError(BaseRAGException):
    """Raised for validation errors."""
    
    def __init__(self, field: str = None, message: str = None, **kwargs):
        self.field = field
        message = message or f"Validation error for field '{field}'"
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class ResourceError(BaseRAGException):
    """Raised for resource-related errors (memory, disk, etc.)."""
    
    def __init__(self, resource_type: str, message: str = None, **kwargs):
        self.resource_type = resource_type
        message = message or f"Resource error: {resource_type}"
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ErrorClassifier:
    """Classifies exceptions into error categories and determines recovery strategies."""
    
    def __init__(self):
        # Order matters - more specific exceptions should come first
        self.classification_rules = [
            # Service errors
            (ConnectionError, ErrorCategory.SERVICE_UNAVAILABLE, ErrorSeverity.HIGH, RecoveryStrategy.RETRY),
            (TimeoutError, ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM, RecoveryStrategy.RETRY),
            
            # Processing errors
            (MemoryError, ErrorCategory.RESOURCE_ERROR, ErrorSeverity.CRITICAL, RecoveryStrategy.GRACEFUL_DEGRADATION),
            (FileNotFoundError, ErrorCategory.PROCESSING_ERROR, ErrorSeverity.MEDIUM, RecoveryStrategy.FALLBACK),
            (PermissionError, ErrorCategory.PROCESSING_ERROR, ErrorSeverity.MEDIUM, RecoveryStrategy.FAIL_FAST),
            
            # Validation errors
            (ValueError, ErrorCategory.VALIDATION_ERROR, ErrorSeverity.LOW, RecoveryStrategy.FAIL_FAST),
            (TypeError, ErrorCategory.VALIDATION_ERROR, ErrorSeverity.LOW, RecoveryStrategy.FAIL_FAST),
        ]
    
    def classify(self, exception: Exception, context: Optional[ErrorContext] = None) -> ErrorInfo:
        """Classify an exception and return error information."""
        exc_type = type(exception)
        
        # Check for custom RAG exceptions first
        if isinstance(exception, BaseRAGException):
            return ErrorInfo(
                category=exception.category,
                severity=exception.severity,
                message=exception.message,
                original_exception=exception.original_exception,
                context=exception.context or context,
                recovery_strategy=self._get_recovery_strategy(exception.category)
            )
        
        # Apply classification rules in order
        for rule_type, category, severity, strategy in self.classification_rules:
            if isinstance(exception, rule_type):
                return ErrorInfo(
                    category=category,
                    severity=severity,
                    message=str(exception),
                    original_exception=exception,
                    context=context,
                    recovery_strategy=strategy
                )
        
        # Check for database-related errors by message content
        if self._is_database_error(exception):
            category, severity, strategy = self._classify_database_error(exception, context)
            return ErrorInfo(
                category=category,
                severity=severity,
                message=str(exception),
                original_exception=exception,
                context=context,
                recovery_strategy=strategy
            )
        
        # Default classification
        return ErrorInfo(
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.MEDIUM,
            message=str(exception),
            original_exception=exception,
            context=context,
            recovery_strategy=RecoveryStrategy.FAIL_FAST
        )
    
    def _is_database_error(self, exception: Exception) -> bool:
        """Check if exception is database-related."""
        error_msg = str(exception).lower()
        db_keywords = ['connection', 'connect', 'timeout', 'lock', 'deadlock', 'busy', 
                      'constraint', 'unique', 'foreign key', 'database', 'sql', 'sqlite']
        return any(keyword in error_msg for keyword in db_keywords)
    
    def _classify_database_error(self, exception: Exception, context: Optional[ErrorContext]) -> tuple:
        """Classify database-related errors."""
        error_msg = str(exception).lower()
        
        if any(keyword in error_msg for keyword in ['connection', 'connect', 'timeout']):
            return ErrorCategory.DATABASE_ERROR, ErrorSeverity.HIGH, RecoveryStrategy.RETRY
        elif any(keyword in error_msg for keyword in ['lock', 'deadlock', 'busy']):
            return ErrorCategory.DATABASE_ERROR, ErrorSeverity.MEDIUM, RecoveryStrategy.RETRY
        elif any(keyword in error_msg for keyword in ['constraint', 'unique', 'foreign key']):
            return ErrorCategory.VALIDATION_ERROR, ErrorSeverity.LOW, RecoveryStrategy.FAIL_FAST
        else:
            return ErrorCategory.DATABASE_ERROR, ErrorSeverity.MEDIUM, RecoveryStrategy.FALLBACK
    
    def _get_recovery_strategy(self, category: ErrorCategory) -> RecoveryStrategy:
        """Get default recovery strategy for error category."""
        strategy_map = {
            ErrorCategory.SERVICE_UNAVAILABLE: RecoveryStrategy.RETRY,
            ErrorCategory.DATABASE_ERROR: RecoveryStrategy.RETRY,
            ErrorCategory.NETWORK_ERROR: RecoveryStrategy.RETRY,
            ErrorCategory.VALIDATION_ERROR: RecoveryStrategy.FAIL_FAST,
            ErrorCategory.PROCESSING_ERROR: RecoveryStrategy.FALLBACK,
            ErrorCategory.RESOURCE_ERROR: RecoveryStrategy.GRACEFUL_DEGRADATION,
            ErrorCategory.CONFIGURATION_ERROR: RecoveryStrategy.FAIL_FAST,
            ErrorCategory.UNKNOWN_ERROR: RecoveryStrategy.FAIL_FAST,
        }
        return strategy_map.get(category, RecoveryStrategy.FAIL_FAST)


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise ServiceUnavailableError(
                        service_name=func.__name__,
                        message=f"Circuit breaker is OPEN for {func.__name__}"
                    )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class RetryHandler:
    """Advanced retry handler with exponential backoff and jitter."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
            ServiceUnavailableError,
            DatabaseError
        ]
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self._execute_with_retry(func, *args, **kwargs)
        return wrapper
    
    def _execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if not self._is_retryable(e) or attempt == self.max_retries:
                    raise e
                
                delay = self._calculate_delay(attempt)
                logging.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                time.sleep(delay)
        
        raise last_exception
    
    def _is_retryable(self, exception: Exception) -> bool:
        """Check if exception is retryable."""
        return any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay


class GracefulDegradation:
    """Handles graceful degradation of non-critical features."""
    
    def __init__(self):
        self.disabled_features = set()
        self.fallback_handlers = {}
    
    def register_fallback(self, feature_name: str, fallback_handler: Callable):
        """Register a fallback handler for a feature."""
        self.fallback_handlers[feature_name] = fallback_handler
    
    def disable_feature(self, feature_name: str, duration: Optional[float] = None):
        """Temporarily disable a feature."""
        self.disabled_features.add(feature_name)
        
        if duration:
            # Schedule re-enabling (in a real implementation, use a proper scheduler)
            import threading
            timer = threading.Timer(duration, lambda: self.enable_feature(feature_name))
            timer.start()
    
    def enable_feature(self, feature_name: str):
        """Re-enable a feature."""
        self.disabled_features.discard(feature_name)
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        return feature_name not in self.disabled_features
    
    def execute_with_fallback(self, feature_name: str, primary_func: Callable, *args, **kwargs) -> Any:
        """Execute function with fallback if feature is disabled."""
        if self.is_feature_enabled(feature_name):
            try:
                return primary_func(*args, **kwargs)
            except Exception as e:
                logging.warning(f"Feature {feature_name} failed: {e}. Using fallback.")
                self.disable_feature(feature_name, duration=300)  # Disable for 5 minutes
        
        # Use fallback
        if feature_name in self.fallback_handlers:
            return self.fallback_handlers[feature_name](*args, **kwargs)
        else:
            logging.warning(f"No fallback available for feature {feature_name}")
            return None


class ErrorHandler:
    """Main error handler that coordinates all error handling strategies."""
    
    def __init__(self):
        self.classifier = ErrorClassifier()
        self.circuit_breakers = {}
        self.graceful_degradation = GracefulDegradation()
        self.logger = logging.getLogger(__name__)
    
    def handle_error(
        self,
        exception: Exception,
        context: Optional[ErrorContext] = None,
        raise_on_critical: bool = True
    ) -> Optional[ErrorInfo]:
        """Handle an error using appropriate strategy."""
        error_info = self.classifier.classify(exception, context)
        
        # Log the error
        self._log_error(error_info)
        
        # Handle based on severity and strategy
        if error_info.severity == ErrorSeverity.CRITICAL and raise_on_critical:
            raise exception
        
        if error_info.recovery_strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            self._handle_graceful_degradation(error_info)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error information."""
        log_data = {
            'category': error_info.category.value,
            'severity': error_info.severity.value,
            'message': error_info.message,
            'timestamp': error_info.timestamp,
            'context': error_info.context.__dict__ if error_info.context else None
        }
        
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(f"Error: {log_data}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Warning: {log_data}")
        else:
            self.logger.info(f"Info: {log_data}")
    
    def _handle_graceful_degradation(self, error_info: ErrorInfo):
        """Handle graceful degradation."""
        if error_info.context and error_info.context.component:
            self.graceful_degradation.disable_feature(
                error_info.context.component,
                duration=300  # 5 minutes
            )
    
    def get_circuit_breaker(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0
    ) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
        return self.circuit_breakers[service_name]
    
    @contextmanager
    def error_context(self, context: ErrorContext):
        """Context manager for error handling."""
        try:
            yield
        except Exception as e:
            self.handle_error(e, context)
            raise


# Global error handler instance
error_handler = ErrorHandler()


# Convenience decorators
def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """Decorator for adding retry logic to functions."""
    return RetryHandler(
        max_retries=max_retries,
        base_delay=base_delay,
        backoff_factor=backoff_factor
    )


def with_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0
):
    """Decorator for adding circuit breaker to functions."""
    return error_handler.get_circuit_breaker(
        service_name=service_name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )


def with_graceful_degradation(feature_name: str, fallback_func: Optional[Callable] = None):
    """Decorator for graceful degradation."""
    def decorator(func: Callable) -> Callable:
        if fallback_func:
            error_handler.graceful_degradation.register_fallback(feature_name, fallback_func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return error_handler.graceful_degradation.execute_with_fallback(
                feature_name, func, *args, **kwargs
            )
        return wrapper
    return decorator


def handle_errors(context: Optional[ErrorContext] = None, raise_on_critical: bool = True):
    """Decorator for automatic error handling."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, context, raise_on_critical)
                if raise_on_critical:
                    raise
                return None
        return wrapper
    return decorator