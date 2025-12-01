"""
Integration tests for system recovery scenarios.
"""
import pytest
import sqlite3
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from utils.health_monitor import (
    HealthMonitor,
    DatabaseHealthChecker,
    ExternalServiceHealthChecker,
    MemoryHealthChecker,
    ServiceRecovery,
    HealthStatus,
    ComponentType,
    setup_default_health_monitoring
)
from utils.error_handler import (
    ErrorHandler,
    ServiceUnavailableError,
    DatabaseError,
    ResourceError,
    ErrorContext,
    with_retry,
    with_circuit_breaker
)


class TestSystemRecoveryIntegration:
    """Test integration between error handling and health monitoring."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.health_monitor = HealthMonitor(check_interval=0.1)  # Fast checks for testing
        self.error_handler = ErrorHandler()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.health_monitor.cleanup()
    
    def test_database_failure_and_recovery(self):
        """Test database failure detection and recovery."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            # Initialize database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            # Add database health checker
            db_checker = DatabaseHealthChecker("test_db", db_path)
            self.health_monitor.add_health_checker(db_checker)
            
            # Register recovery strategy
            recovery_called = []
            
            def db_recovery_strategy(health_result):
                recovery_called.append(True)
                # Simulate successful recovery by recreating the database
                conn = sqlite3.connect(db_path)
                conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
                conn.close()
                return True
            
            self.health_monitor.register_recovery_strategy("test_db", db_recovery_strategy)
            
            # Initial health check should be healthy
            system_health = self.health_monitor.check_system_health()
            assert system_health.overall_status == HealthStatus.HEALTHY
            
            # Simulate database corruption by deleting the file
            Path(db_path).unlink()
            
            # Health check should detect the failure
            system_health = self.health_monitor.check_system_health()
            assert system_health.overall_status == HealthStatus.CRITICAL
            
            # Simulate recovery attempt
            unhealthy_components = system_health.get_critical_components()
            for component in unhealthy_components:
                if component.component_name == "test_db":
                    success = self.health_monitor.service_recovery.attempt_recovery(component)
                    assert success
                    assert len(recovery_called) == 1
            
            # Health check should be healthy again after recovery
            system_health = self.health_monitor.check_system_health()
            assert system_health.overall_status == HealthStatus.HEALTHY
            
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    @patch('requests.get')
    def test_external_service_circuit_breaker_integration(self, mock_get):
        """Test circuit breaker integration with health monitoring."""
        # Set up failing external service
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        # Add external service health checker
        service_checker = ExternalServiceHealthChecker("test_service", "http://example.com/health")
        self.health_monitor.add_health_checker(service_checker)
        
        # Create circuit breaker for the service
        circuit_breaker = self.error_handler.get_circuit_breaker("test_service", failure_threshold=2)
        
        @circuit_breaker
        def call_external_service():
            # This would normally make the actual service call
            response = mock_get("http://example.com/health")
            return response
        
        # First few calls should fail and open the circuit
        with pytest.raises(requests.exceptions.ConnectionError):
            call_external_service()
        
        with pytest.raises(requests.exceptions.ConnectionError):
            call_external_service()
        
        # Circuit should now be open
        with pytest.raises(ServiceUnavailableError):
            call_external_service()
        
        # Health check should also detect the service as unhealthy
        system_health = self.health_monitor.check_system_health()
        assert system_health.overall_status == HealthStatus.CRITICAL
        
        unhealthy_services = [
            comp for comp in system_health.get_critical_components()
            if comp.component_name == "test_service"
        ]
        assert len(unhealthy_services) == 1
    
    def test_memory_pressure_graceful_degradation(self):
        """Test graceful degradation under memory pressure."""
        # Mock high memory usage
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value = Mock(
                total=8*1024**3,
                available=100*1024**2,  # Very low available memory
                used=7.9*1024**3,
                percent=98.0
            )
            
            # Add memory health checker
            memory_checker = MemoryHealthChecker(critical_threshold=95.0)
            self.health_monitor.add_health_checker(memory_checker)
            
            # Register graceful degradation for memory-intensive features
            feature_disabled = []
            
            def disable_heavy_feature(health_result):
                feature_disabled.append("heavy_processing")
                return True
            
            self.health_monitor.register_recovery_strategy("memory", disable_heavy_feature)
            
            # Health check should detect critical memory usage
            system_health = self.health_monitor.check_system_health()
            assert system_health.overall_status == HealthStatus.CRITICAL
            
            # Recovery should be attempted
            critical_components = system_health.get_critical_components()
            memory_component = next(
                (comp for comp in critical_components if comp.component_name == "memory"),
                None
            )
            assert memory_component is not None
            
            success = self.health_monitor.service_recovery.attempt_recovery(memory_component)
            assert success
            assert "heavy_processing" in feature_disabled
    
    def test_connection_pool_failover(self):
        """Test connection pool failover mechanism."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            # Initialize database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            # Add connection pool
            self.health_monitor.add_connection_pool("test_pool", db_path, max_connections=2)
            pool = self.health_monitor.get_connection_pool("test_pool")
            
            # Test normal operation
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test (id) VALUES (1)")
                conn.commit()
            
            # Verify data was inserted
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM test")
                count = cursor.fetchone()[0]
                assert count == 1
            
            # Test concurrent access
            results = []
            
            def concurrent_access():
                try:
                    with pool.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM test")
                        results.append(cursor.fetchone()[0])
                except Exception as e:
                    results.append(f"Error: {e}")
            
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=concurrent_access)
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=5)
            
            # All threads should have succeeded
            assert len(results) == 3
            assert all(isinstance(r, int) and r == 1 for r in results)
            
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_retry_with_health_monitoring(self):
        """Test retry mechanism integration with health monitoring."""
        call_count = 0
        
        @with_retry(max_retries=3, base_delay=0.01)
        def unreliable_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Service temporarily unavailable")
            return "success"
        
        # Operation should succeed after retries
        result = unreliable_operation()
        assert result == "success"
        assert call_count == 3
        
        # Reset for health monitoring test
        call_count = 0
        
        # Add a mock health checker that tracks the service
        service_health_calls = []
        
        class MockServiceChecker:
            def __init__(self):
                self.name = "unreliable_service"
                self.component_type = ComponentType.EXTERNAL_SERVICE
            
            def check_health(self):
                service_health_calls.append(call_count)
                if call_count >= 3:
                    from utils.health_monitor import HealthCheckResult, HealthStatus
                    return HealthCheckResult(
                        self.name, self.component_type, HealthStatus.HEALTHY, "OK", 10.0
                    )
                else:
                    from utils.health_monitor import HealthCheckResult, HealthStatus
                    return HealthCheckResult(
                        self.name, self.component_type, HealthStatus.CRITICAL, "Failing", 0.0
                    )
        
        mock_checker = MockServiceChecker()
        self.health_monitor.add_health_checker(mock_checker)
        
        # Perform operation and health checks
        result = unreliable_operation()
        system_health = self.health_monitor.check_system_health()
        
        assert result == "success"
        assert system_health.overall_status == HealthStatus.HEALTHY
    
    def test_monitoring_loop_integration(self):
        """Test continuous monitoring loop with recovery."""
        # Create a checker that alternates between healthy and unhealthy
        check_count = 0
        recovery_attempts = []
        
        class AlternatingChecker:
            def __init__(self):
                self.name = "alternating_service"
                self.component_type = ComponentType.EXTERNAL_SERVICE
            
            def check_health(self):
                nonlocal check_count
                check_count += 1
                
                from utils.health_monitor import HealthCheckResult, HealthStatus
                if check_count % 2 == 0:
                    return HealthCheckResult(
                        self.name, self.component_type, HealthStatus.HEALTHY, "OK", 10.0
                    )
                else:
                    return HealthCheckResult(
                        self.name, self.component_type, HealthStatus.CRITICAL, "Failing", 0.0
                    )
        
        def recovery_strategy(health_result):
            recovery_attempts.append(health_result.timestamp)
            return True
        
        # Set up monitoring
        checker = AlternatingChecker()
        self.health_monitor.add_health_checker(checker)
        self.health_monitor.register_recovery_strategy("alternating_service", recovery_strategy)
        
        # Start monitoring
        self.health_monitor.start_monitoring()
        
        # Let it run for a short time
        time.sleep(0.5)
        
        # Stop monitoring
        self.health_monitor.stop_monitoring()
        
        # Should have performed multiple checks and recovery attempts
        assert check_count >= 2
        assert len(recovery_attempts) >= 1
        
        # Check health history
        assert len(self.health_monitor.health_history) >= 2
    
    def test_default_setup_integration(self):
        """Test the default health monitoring setup."""
        # Create temporary files for testing
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"
            
            # Create test database
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            # Set up default monitoring (will fail for Ollama, but that's expected)
            monitor = setup_default_health_monitoring(
                db_path=str(db_path),
                data_path=tmp_dir,
                ollama_url="http://localhost:11434"
            )
            
            # Should have all expected checkers
            assert len(monitor.health_checkers) == 5
            
            # Should have connection pool
            assert "chroma" in monitor.connection_pools
            
            # Should have recovery strategies
            assert "ollama" in monitor.service_recovery.recovery_strategies
            assert "file_system" in monitor.service_recovery.recovery_strategies
            
            # Perform health check
            system_health = monitor.check_system_health()
            
            # Database and file system should be healthy
            # Ollama will likely be critical (not running)
            # Memory and CPU should be healthy or warning
            db_results = [r for r in system_health.component_results if r.component_name == "chroma_db"]
            fs_results = [r for r in system_health.component_results if r.component_name == "file_system"]
            
            assert len(db_results) == 1
            assert db_results[0].status == HealthStatus.HEALTHY
            
            assert len(fs_results) == 1
            assert fs_results[0].status in [HealthStatus.HEALTHY, HealthStatus.WARNING]
            
            # Test connection pool
            pool = monitor.get_connection_pool("chroma")
            assert pool is not None
            
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1
            
            # Cleanup
            monitor.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])