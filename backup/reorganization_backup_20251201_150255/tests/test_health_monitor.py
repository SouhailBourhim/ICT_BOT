"""
Unit tests for the health monitoring system.
"""
import pytest
import sqlite3
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from utils.health_monitor import (
    HealthStatus,
    ComponentType,
    HealthCheckResult,
    SystemHealth,
    HealthChecker,
    DatabaseHealthChecker,
    ExternalServiceHealthChecker,
    FileSystemHealthChecker,
    MemoryHealthChecker,
    CPUHealthChecker,
    ConnectionPool,
    ServiceRecovery,
    HealthMonitor,
    create_database_health_checker,
    create_ollama_health_checker,
    create_file_system_health_checker,
    setup_default_health_monitoring,
    health_monitor
)


class TestHealthCheckResult:
    """Test HealthCheckResult class."""
    
    def test_health_check_result_creation(self):
        """Test creating a health check result."""
        result = HealthCheckResult(
            component_name="test_component",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.HEALTHY,
            message="All good",
            response_time_ms=50.0
        )
        
        assert result.component_name == "test_component"
        assert result.component_type == ComponentType.DATABASE
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.response_time_ms == 50.0
        assert isinstance(result.timestamp, datetime)
    
    def test_is_healthy(self):
        """Test is_healthy method."""
        healthy_result = HealthCheckResult(
            component_name="test",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.HEALTHY,
            message="OK",
            response_time_ms=10.0
        )
        
        unhealthy_result = HealthCheckResult(
            component_name="test",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.CRITICAL,
            message="Error",
            response_time_ms=10.0
        )
        
        assert healthy_result.is_healthy()
        assert not unhealthy_result.is_healthy()
    
    def test_is_critical(self):
        """Test is_critical method."""
        critical_result = HealthCheckResult(
            component_name="test",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.CRITICAL,
            message="Critical error",
            response_time_ms=10.0
        )
        
        warning_result = HealthCheckResult(
            component_name="test",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.WARNING,
            message="Warning",
            response_time_ms=10.0
        )
        
        assert critical_result.is_critical()
        assert not warning_result.is_critical()


class TestSystemHealth:
    """Test SystemHealth class."""
    
    def test_system_health_creation(self):
        """Test creating system health."""
        results = [
            HealthCheckResult("comp1", ComponentType.DATABASE, HealthStatus.HEALTHY, "OK", 10.0),
            HealthCheckResult("comp2", ComponentType.EXTERNAL_SERVICE, HealthStatus.WARNING, "Slow", 100.0)
        ]
        
        system_health = SystemHealth(
            overall_status=HealthStatus.WARNING,
            component_results=results
        )
        
        assert system_health.overall_status == HealthStatus.WARNING
        assert len(system_health.component_results) == 2
        assert isinstance(system_health.timestamp, datetime)
    
    def test_get_unhealthy_components(self):
        """Test getting unhealthy components."""
        results = [
            HealthCheckResult("comp1", ComponentType.DATABASE, HealthStatus.HEALTHY, "OK", 10.0),
            HealthCheckResult("comp2", ComponentType.EXTERNAL_SERVICE, HealthStatus.WARNING, "Slow", 100.0),
            HealthCheckResult("comp3", ComponentType.MEMORY, HealthStatus.CRITICAL, "High usage", 5.0)
        ]
        
        system_health = SystemHealth(HealthStatus.CRITICAL, results)
        unhealthy = system_health.get_unhealthy_components()
        
        assert len(unhealthy) == 2
        assert unhealthy[0].component_name == "comp2"
        assert unhealthy[1].component_name == "comp3"
    
    def test_get_critical_components(self):
        """Test getting critical components."""
        results = [
            HealthCheckResult("comp1", ComponentType.DATABASE, HealthStatus.HEALTHY, "OK", 10.0),
            HealthCheckResult("comp2", ComponentType.EXTERNAL_SERVICE, HealthStatus.WARNING, "Slow", 100.0),
            HealthCheckResult("comp3", ComponentType.MEMORY, HealthStatus.CRITICAL, "High usage", 5.0)
        ]
        
        system_health = SystemHealth(HealthStatus.CRITICAL, results)
        critical = system_health.get_critical_components()
        
        assert len(critical) == 1
        assert critical[0].component_name == "comp3"


class TestDatabaseHealthChecker:
    """Test DatabaseHealthChecker class."""
    
    def test_database_health_checker_healthy(self):
        """Test healthy database check."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            # Initialize database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            checker = DatabaseHealthChecker("test_db", db_path)
            result = checker.check_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.component_name == "test_db"
            assert result.component_type == ComponentType.DATABASE
            assert "successful" in result.message.lower()
            assert result.response_time_ms > 0
            assert "database_size_mb" in result.metadata
            
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_database_health_checker_missing_file(self):
        """Test database check with missing file."""
        checker = DatabaseHealthChecker("test_db", "/nonexistent/path.db")
        result = checker.check_health()
        
        assert result.status == HealthStatus.CRITICAL
        assert "not found" in result.message.lower()
    
    def test_database_health_checker_connection_error(self):
        """Test database check with connection error."""
        # Create a directory instead of a file to cause connection error
        with tempfile.TemporaryDirectory() as tmp_dir:
            checker = DatabaseHealthChecker("test_db", tmp_dir)
            result = checker.check_health()
            
            assert result.status == HealthStatus.CRITICAL
            assert ("failed" in result.message.lower() or "error" in result.message.lower())


class TestExternalServiceHealthChecker:
    """Test ExternalServiceHealthChecker class."""
    
    @patch('requests.get')
    def test_external_service_healthy(self, mock_get):
        """Test healthy external service check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_get.return_value = mock_response
        
        checker = ExternalServiceHealthChecker("test_service", "http://example.com/health")
        result = checker.check_health()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.component_name == "test_service"
        assert result.component_type == ComponentType.EXTERNAL_SERVICE
        assert "200" in result.message
        assert result.metadata["status_code"] == 200
    
    @patch('requests.get')
    def test_external_service_unexpected_status(self, mock_get):
        """Test external service with unexpected status code."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        checker = ExternalServiceHealthChecker("test_service", "http://example.com/health")
        result = checker.check_health()
        
        assert result.status == HealthStatus.WARNING
        assert "500" in result.message
    
    @patch('requests.get')
    def test_external_service_timeout(self, mock_get):
        """Test external service timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        checker = ExternalServiceHealthChecker("test_service", "http://example.com/health", timeout=1.0)
        result = checker.check_health()
        
        assert result.status == HealthStatus.CRITICAL
        assert "timeout" in result.message.lower()
    
    @patch('requests.get')
    def test_external_service_connection_error(self, mock_get):
        """Test external service connection error."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        checker = ExternalServiceHealthChecker("test_service", "http://example.com/health")
        result = checker.check_health()
        
        assert result.status == HealthStatus.CRITICAL
        assert "connection failed" in result.message.lower()


class TestFileSystemHealthChecker:
    """Test FileSystemHealthChecker class."""
    
    def test_file_system_healthy(self):
        """Test healthy file system check."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            checker = FileSystemHealthChecker("test_fs", tmp_dir, min_free_space_mb=1.0)
            result = checker.check_health()
            
            # Status could be healthy or warning depending on actual disk usage
            assert result.status in [HealthStatus.HEALTHY, HealthStatus.WARNING]
            assert result.component_name == "test_fs"
            assert result.component_type == ComponentType.FILE_SYSTEM
            assert "total_mb" in result.metadata
            assert "free_mb" in result.metadata
            assert "usage_percent" in result.metadata
    
    def test_file_system_nonexistent_path(self):
        """Test file system check with nonexistent path."""
        checker = FileSystemHealthChecker("test_fs", "/nonexistent/path")
        result = checker.check_health()
        
        assert result.status == HealthStatus.CRITICAL
        assert "does not exist" in result.message.lower()
    
    @patch('shutil.disk_usage')
    def test_file_system_low_space(self, mock_disk_usage):
        """Test file system with low disk space."""
        # Mock disk usage: total=1GB, used=999MB, free=1MB
        mock_disk_usage.return_value = (1024**3, 999*1024**2, 1024**2)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            checker = FileSystemHealthChecker("test_fs", tmp_dir, min_free_space_mb=100.0)
            result = checker.check_health()
            
            assert result.status == HealthStatus.CRITICAL
            assert "low disk space" in result.message.lower()
    
    @patch('shutil.disk_usage')
    def test_file_system_high_usage(self, mock_disk_usage):
        """Test file system with high usage."""
        # Mock disk usage: total=1GB, used=950MB, free=50MB
        mock_disk_usage.return_value = (1024**3, 950*1024**2, 74*1024**2)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            checker = FileSystemHealthChecker("test_fs", tmp_dir, min_free_space_mb=10.0)
            result = checker.check_health()
            
            assert result.status == HealthStatus.WARNING
            assert "high disk usage" in result.message.lower()


class TestMemoryHealthChecker:
    """Test MemoryHealthChecker class."""
    
    @patch('psutil.virtual_memory')
    def test_memory_healthy(self, mock_memory):
        """Test healthy memory check."""
        mock_memory.return_value = Mock(
            total=8*1024**3,  # 8GB
            available=6*1024**3,  # 6GB
            used=2*1024**3,  # 2GB
            percent=25.0
        )
        
        checker = MemoryHealthChecker()
        result = checker.check_health()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.component_name == "memory"
        assert result.component_type == ComponentType.MEMORY
        assert "normal" in result.message.lower()
        assert result.metadata["usage_percent"] == 25.0
    
    @patch('psutil.virtual_memory')
    def test_memory_warning(self, mock_memory):
        """Test memory warning threshold."""
        mock_memory.return_value = Mock(
            total=8*1024**3,
            available=1*1024**3,
            used=7*1024**3,
            percent=85.0
        )
        
        checker = MemoryHealthChecker(warning_threshold=80.0)
        result = checker.check_health()
        
        assert result.status == HealthStatus.WARNING
        assert "high memory usage" in result.message.lower()
    
    @patch('psutil.virtual_memory')
    def test_memory_critical(self, mock_memory):
        """Test memory critical threshold."""
        mock_memory.return_value = Mock(
            total=8*1024**3,
            available=100*1024**2,
            used=7.9*1024**3,
            percent=98.0
        )
        
        checker = MemoryHealthChecker(critical_threshold=95.0)
        result = checker.check_health()
        
        assert result.status == HealthStatus.CRITICAL
        assert "critical memory usage" in result.message.lower()


class TestCPUHealthChecker:
    """Test CPUHealthChecker class."""
    
    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    @patch('psutil.getloadavg')
    def test_cpu_healthy(self, mock_loadavg, mock_cpu_count, mock_cpu_percent):
        """Test healthy CPU check."""
        mock_cpu_percent.return_value = 25.0
        mock_cpu_count.return_value = 4
        mock_loadavg.return_value = (1.0, 1.5, 2.0)
        
        checker = CPUHealthChecker()
        result = checker.check_health()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.component_name == "cpu"
        assert result.component_type == ComponentType.CPU
        assert "normal" in result.message.lower()
        assert result.metadata["cpu_percent"] == 25.0
        assert result.metadata["cpu_count"] == 4
    
    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    def test_cpu_warning(self, mock_cpu_count, mock_cpu_percent):
        """Test CPU warning threshold."""
        mock_cpu_percent.return_value = 85.0
        mock_cpu_count.return_value = 4
        
        checker = CPUHealthChecker(warning_threshold=80.0)
        result = checker.check_health()
        
        assert result.status == HealthStatus.WARNING
        assert "high cpu usage" in result.message.lower()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    def test_cpu_critical(self, mock_cpu_count, mock_cpu_percent):
        """Test CPU critical threshold."""
        mock_cpu_percent.return_value = 98.0
        mock_cpu_count.return_value = 4
        
        checker = CPUHealthChecker(critical_threshold=95.0)
        result = checker.check_health()
        
        assert result.status == HealthStatus.CRITICAL
        assert "critical cpu usage" in result.message.lower()


class TestConnectionPool:
    """Test ConnectionPool class."""
    
    def test_connection_pool_basic_usage(self):
        """Test basic connection pool usage."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            # Initialize database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            pool = ConnectionPool(db_path, max_connections=2)
            
            # Test getting and using connection
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1
            
            pool.close_all()
            
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_connection_pool_multiple_connections(self):
        """Test multiple connections from pool."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            # Initialize database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            pool = ConnectionPool(db_path, max_connections=2)
            
            # Test concurrent connections
            def use_connection():
                with pool.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    time.sleep(0.1)  # Hold connection briefly
                    return cursor.fetchone()[0]
            
            # Start multiple threads
            threads = []
            results = []
            
            def thread_worker():
                results.append(use_connection())
            
            for _ in range(3):
                thread = threading.Thread(target=thread_worker)
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=5)
            
            assert len(results) == 3
            assert all(r == 1 for r in results)
            
            pool.close_all()
            
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestServiceRecovery:
    """Test ServiceRecovery class."""
    
    def test_register_recovery_strategy(self):
        """Test registering recovery strategy."""
        recovery = ServiceRecovery()
        
        def mock_recovery(health_result):
            return True
        
        recovery.register_recovery_strategy("test_component", mock_recovery)
        
        assert "test_component" in recovery.recovery_strategies
        assert recovery.recovery_strategies["test_component"] == mock_recovery
    
    def test_successful_recovery(self):
        """Test successful recovery attempt."""
        recovery = ServiceRecovery()
        
        def mock_recovery(health_result):
            return True
        
        recovery.register_recovery_strategy("test_component", mock_recovery)
        
        health_result = HealthCheckResult(
            component_name="test_component",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.CRITICAL,
            message="Connection failed",
            response_time_ms=0
        )
        
        success = recovery.attempt_recovery(health_result)
        assert success
        
        # Check recovery history
        assert "test_component" in recovery.recovery_history
        history = recovery.recovery_history["test_component"]
        assert history["attempts"] == 0  # Reset on success
        assert history["last_success"] is not None
    
    def test_failed_recovery(self):
        """Test failed recovery attempt."""
        recovery = ServiceRecovery()
        
        def mock_recovery(health_result):
            return False
        
        recovery.register_recovery_strategy("test_component", mock_recovery)
        
        health_result = HealthCheckResult(
            component_name="test_component",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.CRITICAL,
            message="Connection failed",
            response_time_ms=0
        )
        
        success = recovery.attempt_recovery(health_result)
        assert not success
        
        # Check recovery history
        assert "test_component" in recovery.recovery_history
        history = recovery.recovery_history["test_component"]
        assert history["attempts"] == 1
    
    def test_recovery_cooldown(self):
        """Test recovery cooldown mechanism."""
        recovery = ServiceRecovery()
        recovery.max_recovery_attempts = 2
        recovery.recovery_cooldown = 1  # 1 second for testing
        
        def mock_recovery(health_result):
            return False
        
        recovery.register_recovery_strategy("test_component", mock_recovery)
        
        health_result = HealthCheckResult(
            component_name="test_component",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.CRITICAL,
            message="Connection failed",
            response_time_ms=0
        )
        
        # First two attempts should work
        assert recovery.attempt_recovery(health_result) == False
        assert recovery.attempt_recovery(health_result) == False
        
        # Third attempt should be blocked by cooldown
        assert recovery.attempt_recovery(health_result) == False
        
        # Wait for cooldown and try again
        time.sleep(1.1)
        assert recovery.attempt_recovery(health_result) == False


class TestHealthMonitor:
    """Test HealthMonitor class."""
    
    def test_add_health_checker(self):
        """Test adding health checkers."""
        monitor = HealthMonitor()
        
        checker = Mock(spec=HealthChecker)
        monitor.add_health_checker(checker)
        
        assert len(monitor.health_checkers) == 1
        assert monitor.health_checkers[0] == checker
    
    def test_check_system_health(self):
        """Test system health check."""
        monitor = HealthMonitor()
        
        # Create mock checkers
        checker1 = Mock(spec=HealthChecker)
        checker1.check_health.return_value = HealthCheckResult(
            "comp1", ComponentType.DATABASE, HealthStatus.HEALTHY, "OK", 10.0
        )
        
        checker2 = Mock(spec=HealthChecker)
        checker2.check_health.return_value = HealthCheckResult(
            "comp2", ComponentType.EXTERNAL_SERVICE, HealthStatus.WARNING, "Slow", 100.0
        )
        
        monitor.add_health_checker(checker1)
        monitor.add_health_checker(checker2)
        
        system_health = monitor.check_system_health()
        
        assert system_health.overall_status == HealthStatus.WARNING
        assert len(system_health.component_results) == 2
        assert len(monitor.health_history) == 1
    
    def test_determine_overall_status(self):
        """Test overall status determination."""
        monitor = HealthMonitor()
        
        # All healthy
        results = [
            HealthCheckResult("comp1", ComponentType.DATABASE, HealthStatus.HEALTHY, "OK", 10.0),
            HealthCheckResult("comp2", ComponentType.EXTERNAL_SERVICE, HealthStatus.HEALTHY, "OK", 10.0)
        ]
        assert monitor._determine_overall_status(results) == HealthStatus.HEALTHY
        
        # One warning
        results[1] = HealthCheckResult("comp2", ComponentType.EXTERNAL_SERVICE, HealthStatus.WARNING, "Slow", 100.0)
        assert monitor._determine_overall_status(results) == HealthStatus.WARNING
        
        # One critical
        results[1] = HealthCheckResult("comp2", ComponentType.EXTERNAL_SERVICE, HealthStatus.CRITICAL, "Down", 0.0)
        assert monitor._determine_overall_status(results) == HealthStatus.CRITICAL
        
        # Empty results
        assert monitor._determine_overall_status([]) == HealthStatus.UNKNOWN
    
    def test_get_health_summary(self):
        """Test getting health summary."""
        monitor = HealthMonitor()
        
        # No data
        summary = monitor.get_health_summary()
        assert summary["status"] == "no_data"
        
        # Add some health data
        checker = Mock(spec=HealthChecker)
        checker.check_health.return_value = HealthCheckResult(
            "comp1", ComponentType.DATABASE, HealthStatus.HEALTHY, "OK", 10.0,
            metadata={"test": "value"}
        )
        
        monitor.add_health_checker(checker)
        monitor.check_system_health()
        
        summary = monitor.get_health_summary()
        assert summary["overall_status"] == "healthy"
        assert "comp1" in summary["components"]
        assert summary["components"]["comp1"]["status"] == "healthy"
        assert summary["components"]["comp1"]["metadata"]["test"] == "value"


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_create_database_health_checker(self):
        """Test creating database health checker."""
        checker = create_database_health_checker("test_db", "test.db")
        
        assert isinstance(checker, DatabaseHealthChecker)
        assert checker.name == "test_db"
        assert checker.db_path == "test.db"
    
    def test_create_ollama_health_checker(self):
        """Test creating Ollama health checker."""
        checker = create_ollama_health_checker("http://localhost:11434")
        
        assert isinstance(checker, ExternalServiceHealthChecker)
        assert checker.name == "ollama"
        assert checker.url == "http://localhost:11434/api/tags"
    
    def test_create_file_system_health_checker(self):
        """Test creating file system health checker."""
        checker = create_file_system_health_checker("/tmp", 50.0)
        
        assert isinstance(checker, FileSystemHealthChecker)
        assert checker.name == "file_system"
        assert checker.path == "/tmp"
        assert checker.min_free_space_mb == 50.0
    
    def test_setup_default_health_monitoring(self):
        """Test setting up default health monitoring."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"
            
            # Create test database
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            monitor = setup_default_health_monitoring(
                db_path=str(db_path),
                data_path=tmp_dir,
                ollama_url="http://localhost:11434"
            )
            
            assert len(monitor.health_checkers) == 5  # DB, Ollama, FS, Memory, CPU
            assert "chroma" in monitor.connection_pools
            assert "ollama" in monitor.service_recovery.recovery_strategies
            assert "file_system" in monitor.service_recovery.recovery_strategies


if __name__ == "__main__":
    pytest.main([__file__])