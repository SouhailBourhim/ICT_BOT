"""
Unit tests for the error handling system.
"""
import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from src.utils.error_handler import (
    ErrorSeverity,
    ErrorCategory,
    RecoveryStrategy,
    ErrorContext,
    ErrorInfo,
    BaseRAGException,
    ServiceUnavailableError,
    DatabaseError,
    ProcessingError,
    ValidationError,
    ResourceError,
    ErrorClassifier,
    CircuitBreaker,
    RetryHandler,
    GracefulDegradation,
    ErrorHandler,
    with_retry,
    with_circuit_breaker,
    with_graceful_degradation,
    handle_errors,
    error_handler
)


class TestErrorClasses:
    """Test custom error classes."""
    
    def test_base_rag_exception(self):
        """Test BaseRAGException initialization."""
        context = ErrorContext(operation="test", component="test_component")
        original_exc = ValueError("original error")
        
        exc = BaseRAGException(
            message="Test error",
            category=ErrorCategory.PROCESSING_ERROR,
            severity=ErrorSeverity.HIGH,
            context=context,
            original_exception=original_exc
        )
        
        assert exc.message == "Test error"
        assert exc.category == ErrorCategory.PROCESSING_ERROR
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.context == context
        assert exc.original_exception == original_exc
        assert exc.timestamp > 0
    
    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError."""
        exc = ServiceUnavailableError("ollama")
        
        assert exc.service_name == "ollama"
        assert exc.category == ErrorCategory.SERVICE_UNAVAILABLE
        assert exc.severity == ErrorSeverity.HIGH
        assert "ollama" in exc.message
    
    def test_database_error(self):
        """Test DatabaseError."""
        exc = DatabaseError("insert")
        
        assert exc.operation == "insert"
        assert exc.category == ErrorCategory.DATABASE_ERROR
        assert exc.severity == ErrorSeverity.HIGH
        assert "insert" in exc.message
    
    def test_processing_error(self):
        """Test ProcessingError."""
        exc = ProcessingError("doc123")
        
        assert exc.document_id == "doc123"
        assert exc.category == ErrorCategory.PROCESSING_ERROR
        assert exc.severity == ErrorSeverity.MEDIUM
        assert "doc123" in exc.message
    
    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError("email")
        
        assert exc.field == "email"
        assert exc.category == ErrorCategory.VALIDATION_ERROR
        assert exc.severity == ErrorSeverity.LOW
        assert "email" in exc.message
    
    def test_resource_error(self):
        """Test ResourceError."""
        exc = ResourceError("memory")
        
        assert exc.resource_type == "memory"
        assert exc.category == ErrorCategory.RESOURCE_ERROR
        assert exc.severity == ErrorSeverity.HIGH
        assert "memory" in exc.message


class TestErrorClassifier:
    """Test error classification."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = ErrorClassifier()
    
    def test_classify_custom_exception(self):
        """Test classification of custom RAG exceptions."""
        exc = ServiceUnavailableError("test_service")
        context = ErrorContext(operation="test", component="test_component")
        
        error_info = self.classifier.classify(exc, context)
        
        assert error_info.category == ErrorCategory.SERVICE_UNAVAILABLE
        assert error_info.severity == ErrorSeverity.HIGH
        assert error_info.original_exception == exc.original_exception
        assert error_info.context == exc.context or context
    
    def test_classify_connection_error(self):
        """Test classification of connection errors."""
        exc = ConnectionError("Connection failed")
        
        error_info = self.classifier.classify(exc)
        
        assert error_info.category == ErrorCategory.SERVICE_UNAVAILABLE
        assert error_info.severity == ErrorSeverity.HIGH
        assert error_info.recovery_strategy == RecoveryStrategy.RETRY
        assert error_info.original_exception == exc
    
    def test_classify_timeout_error(self):
        """Test classification of timeout errors."""
        exc = TimeoutError("Request timed out")
        
        error_info = self.classifier.classify(exc)
        
        assert error_info.category == ErrorCategory.NETWORK_ERROR
        assert error_info.severity == ErrorSeverity.MEDIUM
        assert error_info.recovery_strategy == RecoveryStrategy.RETRY
    
    def test_classify_memory_error(self):
        """Test classification of memory errors."""
        exc = MemoryError("Out of memory")
        
        error_info = self.classifier.classify(exc)
        
        assert error_info.category == ErrorCategory.RESOURCE_ERROR
        assert error_info.severity == ErrorSeverity.CRITICAL
        assert error_info.recovery_strategy == RecoveryStrategy.GRACEFUL_DEGRADATION
    
    def test_classify_value_error(self):
        """Test classification of validation errors."""
        exc = ValueError("Invalid value")
        
        error_info = self.classifier.classify(exc)
        
        assert error_info.category == ErrorCategory.VALIDATION_ERROR
        assert error_info.severity == ErrorSeverity.LOW
        assert error_info.recovery_strategy == RecoveryStrategy.FAIL_FAST
    
    def test_classify_unknown_error(self):
        """Test classification of unknown errors."""
        exc = RuntimeError("Unknown error")
        
        error_info = self.classifier.classify(exc)
        
        assert error_info.category == ErrorCategory.UNKNOWN_ERROR
        assert error_info.severity == ErrorSeverity.MEDIUM
        assert error_info.recovery_strategy == RecoveryStrategy.FAIL_FAST
    
    def test_classify_database_connection_error(self):
        """Test classification of database connection errors."""
        exc = Exception("connection timeout")
        
        error_info = self.classifier.classify(exc)
        
        assert error_info.category == ErrorCategory.DATABASE_ERROR
        assert error_info.severity == ErrorSeverity.HIGH
        assert error_info.recovery_strategy == RecoveryStrategy.RETRY


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        
        @breaker
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_open_state(self):
        """Test circuit breaker opening after failures."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
        
        @breaker
        def failing_function():
            raise ConnectionError("Connection failed")
        
        # First failure
        with pytest.raises(ConnectionError):
            failing_function()
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 1
        
        # Second failure - should open circuit
        with pytest.raises(ConnectionError):
            failing_function()
        assert breaker.state == "OPEN"
        assert breaker.failure_count == 2
        
        # Third call should raise ServiceUnavailableError
        with pytest.raises(ServiceUnavailableError):
            failing_function()
    
    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state and recovery."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        call_count = 0
        
        @breaker
        def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise ConnectionError("Connection failed")
            return "success"
        
        # First call fails, opens circuit
        with pytest.raises(ConnectionError):
            sometimes_failing_function()
        assert breaker.state == "OPEN"
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Next call should succeed and close circuit
        result = sometimes_failing_function()
        assert result == "success"
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0


class TestRetryHandler:
    """Test retry handler functionality."""
    
    def test_retry_success_on_first_attempt(self):
        """Test successful execution on first attempt."""
        retry_handler = RetryHandler(max_retries=3, base_delay=0.1)
        
        @retry_handler
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_retry_success_after_failures(self):
        """Test successful execution after some failures."""
        retry_handler = RetryHandler(max_retries=3, base_delay=0.01)
        
        call_count = 0
        
        @retry_handler
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Connection failed")
            return "success"
        
        result = eventually_successful_function()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhaustion(self):
        """Test retry exhaustion."""
        retry_handler = RetryHandler(max_retries=2, base_delay=0.01)
        
        @retry_handler
        def always_failing_function():
            raise ConnectionError("Connection failed")
        
        with pytest.raises(ConnectionError):
            always_failing_function()
    
    def test_retry_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        retry_handler = RetryHandler(max_retries=3, base_delay=0.01)
        
        call_count = 0
        
        @retry_handler
        def function_with_validation_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid value")
        
        with pytest.raises(ValueError):
            function_with_validation_error()
        
        # Should only be called once (no retries for ValueError)
        assert call_count == 1
    
    def test_retry_delay_calculation(self):
        """Test retry delay calculation."""
        retry_handler = RetryHandler(
            max_retries=3,
            base_delay=1.0,
            backoff_factor=2.0,
            jitter=False
        )
        
        # Test delay calculation
        assert retry_handler._calculate_delay(0) == 1.0
        assert retry_handler._calculate_delay(1) == 2.0
        assert retry_handler._calculate_delay(2) == 4.0
    
    def test_retry_with_jitter(self):
        """Test retry with jitter."""
        retry_handler = RetryHandler(
            max_retries=3,
            base_delay=1.0,
            backoff_factor=2.0,
            jitter=True
        )
        
        delay = retry_handler._calculate_delay(1)
        # With jitter, delay should be between 1.0 and 2.0
        assert 1.0 <= delay <= 2.0


class TestGracefulDegradation:
    """Test graceful degradation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.degradation = GracefulDegradation()
    
    def test_feature_enable_disable(self):
        """Test enabling and disabling features."""
        feature_name = "test_feature"
        
        # Feature should be enabled by default
        assert self.degradation.is_feature_enabled(feature_name)
        
        # Disable feature
        self.degradation.disable_feature(feature_name)
        assert not self.degradation.is_feature_enabled(feature_name)
        
        # Re-enable feature
        self.degradation.enable_feature(feature_name)
        assert self.degradation.is_feature_enabled(feature_name)
    
    def test_fallback_registration_and_execution(self):
        """Test fallback handler registration and execution."""
        feature_name = "test_feature"
        
        def primary_function(x):
            raise Exception("Primary function failed")
        
        def fallback_function(x):
            return f"fallback_{x}"
        
        # Register fallback
        self.degradation.register_fallback(feature_name, fallback_function)
        
        # Execute with fallback
        result = self.degradation.execute_with_fallback(
            feature_name, primary_function, "test"
        )
        
        assert result == "fallback_test"
        assert not self.degradation.is_feature_enabled(feature_name)
    
    def test_execute_without_fallback(self):
        """Test execution when no fallback is available."""
        feature_name = "test_feature"
        
        def primary_function(x):
            raise Exception("Primary function failed")
        
        # Execute without fallback
        result = self.degradation.execute_with_fallback(
            feature_name, primary_function, "test"
        )
        
        assert result is None
        assert not self.degradation.is_feature_enabled(feature_name)
    
    def test_successful_primary_execution(self):
        """Test successful primary function execution."""
        feature_name = "test_feature"
        
        def primary_function(x):
            return f"primary_{x}"
        
        result = self.degradation.execute_with_fallback(
            feature_name, primary_function, "test"
        )
        
        assert result == "primary_test"
        assert self.degradation.is_feature_enabled(feature_name)


class TestErrorHandler:
    """Test main error handler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()
    
    def test_handle_error_logging(self):
        """Test error logging."""
        context = ErrorContext(operation="test", component="test_component")
        exception = ValueError("Test error")
        
        with patch.object(self.handler.logger, 'info') as mock_log:
            error_info = self.handler.handle_error(exception, context, raise_on_critical=False)
            
            assert error_info.category == ErrorCategory.VALIDATION_ERROR
            assert error_info.severity == ErrorSeverity.LOW
            mock_log.assert_called_once()
    
    def test_handle_critical_error(self):
        """Test handling of critical errors."""
        exception = MemoryError("Out of memory")
        
        with pytest.raises(MemoryError):
            self.handler.handle_error(exception, raise_on_critical=True)
    
    def test_handle_graceful_degradation(self):
        """Test graceful degradation handling."""
        context = ErrorContext(operation="test", component="test_component")
        exception = MemoryError("Out of memory")
        
        self.handler.handle_error(exception, context, raise_on_critical=False)
        
        # Component should be disabled
        assert not self.handler.graceful_degradation.is_feature_enabled("test_component")
    
    def test_get_circuit_breaker(self):
        """Test circuit breaker creation and retrieval."""
        breaker1 = self.handler.get_circuit_breaker("service1")
        breaker2 = self.handler.get_circuit_breaker("service1")
        breaker3 = self.handler.get_circuit_breaker("service2")
        
        # Same service should return same breaker
        assert breaker1 is breaker2
        
        # Different service should return different breaker
        assert breaker1 is not breaker3
    
    def test_error_context_manager(self):
        """Test error context manager."""
        context = ErrorContext(operation="test", component="test_component")
        
        with patch.object(self.handler, 'handle_error') as mock_handle:
            with pytest.raises(ValueError):
                with self.handler.error_context(context):
                    raise ValueError("Test error")
            
            mock_handle.assert_called_once()


class TestDecorators:
    """Test error handling decorators."""
    
    def test_with_retry_decorator(self):
        """Test retry decorator."""
        call_count = 0
        
        @with_retry(max_retries=2, base_delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise ConnectionError("Connection failed")
            return "success"
        
        result = test_function()
        assert result == "success"
        assert call_count == 2
    
    def test_with_circuit_breaker_decorator(self):
        """Test circuit breaker decorator."""
        @with_circuit_breaker("test_service", failure_threshold=1)
        def test_function():
            raise ConnectionError("Connection failed")
        
        # First call should fail normally
        with pytest.raises(ConnectionError):
            test_function()
        
        # Second call should raise ServiceUnavailableError (circuit open)
        with pytest.raises(ServiceUnavailableError):
            test_function()
    
    def test_with_graceful_degradation_decorator(self):
        """Test graceful degradation decorator."""
        def fallback_function():
            return "fallback"
        
        @with_graceful_degradation("test_feature", fallback_function)
        def test_function():
            raise Exception("Primary function failed")
        
        result = test_function()
        assert result == "fallback"
    
    def test_handle_errors_decorator(self):
        """Test handle errors decorator."""
        context = ErrorContext(operation="test", component="test_component")
        
        @handle_errors(context=context, raise_on_critical=False)
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        assert result is None  # Should return None when error is handled
    
    def test_handle_errors_decorator_with_critical(self):
        """Test handle errors decorator with critical error."""
        @handle_errors(raise_on_critical=True)
        def test_function():
            raise MemoryError("Out of memory")
        
        with pytest.raises(MemoryError):
            test_function()


class TestIntegration:
    """Test integration scenarios."""
    
    def test_combined_error_handling(self):
        """Test combination of multiple error handling strategies."""
        call_count = 0
        
        @with_retry(max_retries=2, base_delay=0.01)
        @with_circuit_breaker("combined_service", failure_threshold=3)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Connection failed")
            return "success"
        
        result = test_function()
        assert result == "success"
        assert call_count == 3  # Initial call + 2 retries
    
    def test_error_context_with_metadata(self):
        """Test error context with metadata."""
        context = ErrorContext(
            operation="document_processing",
            component="pdf_processor",
            user_id="user123",
            session_id="session456",
            metadata={"document_id": "doc789", "page": 5}
        )
        
        exception = ProcessingError("doc789", "Failed to process page 5")
        
        error_info = error_handler.classifier.classify(exception, context)
        
        assert error_info.context == context
        assert error_info.context.metadata["document_id"] == "doc789"
        assert error_info.context.metadata["page"] == 5


if __name__ == "__main__":
    pytest.main([__file__])