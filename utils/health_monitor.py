"""
System health monitoring and recovery utilities.
Provides health checks, service monitoring, and automatic recovery mechanisms.
"""
import asyncio
import logging
import psutil
import sqlite3
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import requests
from contextlib import contextmanager

from utils.error_handler import (
    ErrorHandler, 
    ServiceUnavailableError, 
    DatabaseError, 
    ResourceError,
    ErrorContext,
    with_retry
)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """Types of system components."""
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    FILE_SYSTEM = "file_system"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    APPLICATION = "application"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    component_name: str
    component_type: ComponentType
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self.status == HealthStatus.HEALTHY
    
    def is_critical(self) -> bool:
        """Check if component is in critical state."""
        return self.status == HealthStatus.CRITICAL


@dataclass
class SystemHealth:
    """Overall system health status."""
    overall_status: HealthStatus
    component_results: List[HealthCheckResult]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def get_unhealthy_components(self) -> List[HealthCheckResult]:
        """Get list of unhealthy components."""
        return [result for result in self.component_results if not result.is_healthy()]
    
    def get_critical_components(self) -> List[HealthCheckResult]:
        """Get list of critical components."""
        return [result for result in self.component_results if result.is_critical()]


class HealthChecker(ABC):
    """Abstract base class for health checkers."""
    
    def __init__(self, name: str, component_type: ComponentType, timeout: float = 5.0):
        self.name = name
        self.component_type = component_type
        self.timeout = timeout
    
    @abstractmethod
    def check_health(self) -> HealthCheckResult:
        """Perform health check and return result."""
        pass
    
    def _create_result(
        self, 
        status: HealthStatus, 
        message: str, 
        response_time_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HealthCheckResult:
        """Create health check result."""
        return HealthCheckResult(
            component_name=self.name,
            component_type=self.component_type,
            status=status,
            message=message,
            response_time_ms=response_time_ms,
            metadata=metadata or {}
        )


class DatabaseHealthChecker(HealthChecker):
    """Health checker for database connections."""
    
    def __init__(self, name: str, db_path: str, timeout: float = 5.0):
        super().__init__(name, ComponentType.DATABASE, timeout)
        self.db_path = db_path
    
    def check_health(self) -> HealthCheckResult:
        """Check database health."""
        start_time = time.time()
        
        try:
            # Check if database file exists
            if not Path(self.db_path).exists():
                return self._create_result(
                    HealthStatus.CRITICAL,
                    f"Database file not found: {self.db_path}",
                    (time.time() - start_time) * 1000
                )
            
            # Test database connection and basic query
            with sqlite3.connect(self.db_path, timeout=self.timeout) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    response_time = (time.time() - start_time) * 1000
                    
                    # Get database statistics
                    cursor.execute("PRAGMA database_list")
                    db_info = cursor.fetchall()
                    
                    cursor.execute("PRAGMA page_count")
                    page_count = cursor.fetchone()[0]
                    
                    cursor.execute("PRAGMA page_size")
                    page_size = cursor.fetchone()[0]
                    
                    db_size_mb = (page_count * page_size) / (1024 * 1024)
                    
                    metadata = {
                        "database_size_mb": round(db_size_mb, 2),
                        "page_count": page_count,
                        "page_size": page_size
                    }
                    
                    return self._create_result(
                        HealthStatus.HEALTHY,
                        "Database connection successful",
                        response_time,
                        metadata
                    )
                else:
                    return self._create_result(
                        HealthStatus.CRITICAL,
                        "Database query failed",
                        (time.time() - start_time) * 1000
                    )
                    
        except sqlite3.OperationalError as e:
            return self._create_result(
                HealthStatus.CRITICAL,
                f"Database operational error: {str(e)}",
                (time.time() - start_time) * 1000
            )
        except Exception as e:
            return self._create_result(
                HealthStatus.CRITICAL,
                f"Database connection failed: {str(e)}",
                (time.time() - start_time) * 1000
            )


class ExternalServiceHealthChecker(HealthChecker):
    """Health checker for external services."""
    
    def __init__(self, name: str, url: str, timeout: float = 5.0, expected_status: int = 200):
        super().__init__(name, ComponentType.EXTERNAL_SERVICE, timeout)
        self.url = url
        self.expected_status = expected_status
    
    def check_health(self) -> HealthCheckResult:
        """Check external service health."""
        start_time = time.time()
        
        try:
            response = requests.get(self.url, timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == self.expected_status:
                metadata = {
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers)
                }
                return self._create_result(
                    HealthStatus.HEALTHY,
                    f"Service responding normally (HTTP {response.status_code})",
                    response_time,
                    metadata
                )
            else:
                return self._create_result(
                    HealthStatus.WARNING,
                    f"Unexpected status code: {response.status_code}",
                    response_time,
                    {"status_code": response.status_code}
                )
                
        except requests.exceptions.Timeout:
            return self._create_result(
                HealthStatus.CRITICAL,
                f"Service timeout after {self.timeout}s",
                (time.time() - start_time) * 1000
            )
        except requests.exceptions.ConnectionError:
            return self._create_result(
                HealthStatus.CRITICAL,
                "Service connection failed",
                (time.time() - start_time) * 1000
            )
        except Exception as e:
            return self._create_result(
                HealthStatus.CRITICAL,
                f"Service check failed: {str(e)}",
                (time.time() - start_time) * 1000
            )


class FileSystemHealthChecker(HealthChecker):
    """Health checker for file system resources."""
    
    def __init__(self, name: str, path: str, min_free_space_mb: float = 100.0):
        super().__init__(name, ComponentType.FILE_SYSTEM)
        self.path = path
        self.min_free_space_mb = min_free_space_mb
    
    def check_health(self) -> HealthCheckResult:
        """Check file system health."""
        start_time = time.time()
        
        try:
            # Check if path exists
            path_obj = Path(self.path)
            if not path_obj.exists():
                return self._create_result(
                    HealthStatus.CRITICAL,
                    f"Path does not exist: {self.path}",
                    (time.time() - start_time) * 1000
                )
            
            # Get disk usage
            import shutil
            total, used, free = shutil.disk_usage(self.path)
            
            total_mb = total / (1024 * 1024)
            used_mb = used / (1024 * 1024)
            free_mb = free / (1024 * 1024)
            usage_percent = (used / total) * 100
            
            metadata = {
                "total_mb": round(total_mb, 2),
                "used_mb": round(used_mb, 2),
                "free_mb": round(free_mb, 2),
                "usage_percent": round(usage_percent, 2)
            }
            
            response_time = (time.time() - start_time) * 1000
            
            if free_mb < self.min_free_space_mb:
                return self._create_result(
                    HealthStatus.CRITICAL,
                    f"Low disk space: {free_mb:.1f}MB free (minimum: {self.min_free_space_mb}MB)",
                    response_time,
                    metadata
                )
            elif usage_percent > 90:
                return self._create_result(
                    HealthStatus.WARNING,
                    f"High disk usage: {usage_percent:.1f}%",
                    response_time,
                    metadata
                )
            else:
                return self._create_result(
                    HealthStatus.HEALTHY,
                    f"File system healthy: {free_mb:.1f}MB free ({usage_percent:.1f}% used)",
                    response_time,
                    metadata
                )
                
        except Exception as e:
            return self._create_result(
                HealthStatus.CRITICAL,
                f"File system check failed: {str(e)}",
                (time.time() - start_time) * 1000
            )


class MemoryHealthChecker(HealthChecker):
    """Health checker for memory usage."""
    
    def __init__(self, name: str = "memory", warning_threshold: float = 80.0, critical_threshold: float = 95.0):
        super().__init__(name, ComponentType.MEMORY)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    def check_health(self) -> HealthCheckResult:
        """Check memory health."""
        start_time = time.time()
        
        try:
            # Get system memory info
            memory = psutil.virtual_memory()
            
            metadata = {
                "total_mb": round(memory.total / (1024 * 1024), 2),
                "available_mb": round(memory.available / (1024 * 1024), 2),
                "used_mb": round(memory.used / (1024 * 1024), 2),
                "usage_percent": memory.percent
            }
            
            response_time = (time.time() - start_time) * 1000
            
            if memory.percent >= self.critical_threshold:
                return self._create_result(
                    HealthStatus.CRITICAL,
                    f"Critical memory usage: {memory.percent:.1f}%",
                    response_time,
                    metadata
                )
            elif memory.percent >= self.warning_threshold:
                return self._create_result(
                    HealthStatus.WARNING,
                    f"High memory usage: {memory.percent:.1f}%",
                    response_time,
                    metadata
                )
            else:
                return self._create_result(
                    HealthStatus.HEALTHY,
                    f"Memory usage normal: {memory.percent:.1f}%",
                    response_time,
                    metadata
                )
                
        except Exception as e:
            return self._create_result(
                HealthStatus.CRITICAL,
                f"Memory check failed: {str(e)}",
                (time.time() - start_time) * 1000
            )


class CPUHealthChecker(HealthChecker):
    """Health checker for CPU usage."""
    
    def __init__(self, name: str = "cpu", warning_threshold: float = 80.0, critical_threshold: float = 95.0):
        super().__init__(name, ComponentType.CPU)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    def check_health(self) -> HealthCheckResult:
        """Check CPU health."""
        start_time = time.time()
        
        try:
            # Get CPU usage (average over 1 second)
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Get load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()
                load_avg_1min = load_avg[0]
            except (AttributeError, OSError):
                # Windows doesn't have load average
                load_avg_1min = None
            
            metadata = {
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "load_avg_1min": load_avg_1min
            }
            
            response_time = (time.time() - start_time) * 1000
            
            if cpu_percent >= self.critical_threshold:
                return self._create_result(
                    HealthStatus.CRITICAL,
                    f"Critical CPU usage: {cpu_percent:.1f}%",
                    response_time,
                    metadata
                )
            elif cpu_percent >= self.warning_threshold:
                return self._create_result(
                    HealthStatus.WARNING,
                    f"High CPU usage: {cpu_percent:.1f}%",
                    response_time,
                    metadata
                )
            else:
                return self._create_result(
                    HealthStatus.HEALTHY,
                    f"CPU usage normal: {cpu_percent:.1f}%",
                    response_time,
                    metadata
                )
                
        except Exception as e:
            return self._create_result(
                HealthStatus.CRITICAL,
                f"CPU check failed: {str(e)}",
                (time.time() - start_time) * 1000
            )


class ConnectionPool:
    """Simple connection pool for database connections."""
    
    def __init__(self, db_path: str, max_connections: int = 10, timeout: float = 30.0):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool = []
        self._used_connections = set()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        conn = None
        try:
            conn = self._acquire_connection()
            yield conn
        finally:
            if conn:
                self._release_connection(conn)
    
    def _acquire_connection(self) -> sqlite3.Connection:
        """Acquire a connection from the pool."""
        with self._condition:
            # For SQLite, we need to create a new connection per thread
            # due to threading restrictions
            conn = sqlite3.connect(
                self.db_path, 
                timeout=self.timeout,
                check_same_thread=False  # Allow cross-thread usage
            )
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            
            self._used_connections.add(conn)
            return conn
    
    def _release_connection(self, conn: sqlite3.Connection):
        """Release a connection back to the pool."""
        with self._condition:
            if conn in self._used_connections:
                self._used_connections.remove(conn)
                
                # For SQLite, we close the connection immediately
                # rather than pooling due to threading restrictions
                try:
                    conn.close()
                except:
                    pass
                
                self._condition.notify()
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._pool:
                try:
                    conn.close()
                except:
                    pass
            self._pool.clear()
            
            for conn in self._used_connections.copy():
                try:
                    conn.close()
                except:
                    pass
            self._used_connections.clear()


class ServiceRecovery:
    """Handles automatic service recovery."""
    
    def __init__(self):
        self.recovery_strategies = {}
        self.recovery_history = {}
        self.max_recovery_attempts = 3
        self.recovery_cooldown = 300  # 5 minutes
        self.logger = logging.getLogger(__name__)
    
    def register_recovery_strategy(self, component_name: str, recovery_func: Callable):
        """Register a recovery strategy for a component."""
        self.recovery_strategies[component_name] = recovery_func
    
    def attempt_recovery(self, health_result: HealthCheckResult) -> bool:
        """Attempt to recover a failed component."""
        component_name = health_result.component_name
        
        if component_name not in self.recovery_strategies:
            self.logger.warning(f"No recovery strategy for component: {component_name}")
            return False
        
        # Check recovery history
        if not self._can_attempt_recovery(component_name):
            self.logger.warning(f"Recovery cooldown active for component: {component_name}")
            return False
        
        try:
            self.logger.info(f"Attempting recovery for component: {component_name}")
            recovery_func = self.recovery_strategies[component_name]
            success = recovery_func(health_result)
            
            # Update recovery history
            self._update_recovery_history(component_name, success)
            
            if success:
                self.logger.info(f"Recovery successful for component: {component_name}")
            else:
                self.logger.error(f"Recovery failed for component: {component_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Recovery attempt failed for {component_name}: {e}")
            self._update_recovery_history(component_name, False)
            return False
    
    def _can_attempt_recovery(self, component_name: str) -> bool:
        """Check if recovery can be attempted for a component."""
        if component_name not in self.recovery_history:
            return True
        
        history = self.recovery_history[component_name]
        
        # Check if max attempts exceeded
        if history['attempts'] >= self.max_recovery_attempts:
            # Check if cooldown period has passed
            if time.time() - history['last_attempt'] < self.recovery_cooldown:
                return False
            else:
                # Reset attempts after cooldown
                history['attempts'] = 0
        
        return True
    
    def _update_recovery_history(self, component_name: str, success: bool):
        """Update recovery history for a component."""
        if component_name not in self.recovery_history:
            self.recovery_history[component_name] = {
                'attempts': 0,
                'last_attempt': 0,
                'last_success': None
            }
        
        history = self.recovery_history[component_name]
        history['attempts'] += 1
        history['last_attempt'] = time.time()
        
        if success:
            history['last_success'] = time.time()
            history['attempts'] = 0  # Reset attempts on success


class HealthMonitor:
    """Main health monitoring system."""
    
    def __init__(self, check_interval: float = 60.0):
        self.check_interval = check_interval
        self.health_checkers: List[HealthChecker] = []
        self.service_recovery = ServiceRecovery()
        self.connection_pools: Dict[str, ConnectionPool] = {}
        self.monitoring_active = False
        self.monitoring_thread = None
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler()
        
        # Health check history
        self.health_history: List[SystemHealth] = []
        self.max_history_size = 100
    
    def add_health_checker(self, checker: HealthChecker):
        """Add a health checker to the monitor."""
        self.health_checkers.append(checker)
    
    def add_connection_pool(self, name: str, db_path: str, max_connections: int = 10):
        """Add a connection pool for database failover."""
        self.connection_pools[name] = ConnectionPool(db_path, max_connections)
    
    def get_connection_pool(self, name: str) -> Optional[ConnectionPool]:
        """Get a connection pool by name."""
        return self.connection_pools.get(name)
    
    def register_recovery_strategy(self, component_name: str, recovery_func: Callable):
        """Register a recovery strategy for a component."""
        self.service_recovery.register_recovery_strategy(component_name, recovery_func)
    
    def check_system_health(self) -> SystemHealth:
        """Perform health checks on all components."""
        results = []
        
        with ThreadPoolExecutor(max_workers=len(self.health_checkers)) as executor:
            # Submit all health checks
            future_to_checker = {
                executor.submit(checker.check_health): checker 
                for checker in self.health_checkers
            }
            
            # Collect results
            for future in future_to_checker:
                try:
                    result = future.result(timeout=30)  # 30 second timeout per check
                    results.append(result)
                except FutureTimeoutError:
                    checker = future_to_checker[future]
                    results.append(HealthCheckResult(
                        component_name=checker.name,
                        component_type=checker.component_type,
                        status=HealthStatus.CRITICAL,
                        message="Health check timed out",
                        response_time_ms=30000
                    ))
                except Exception as e:
                    checker = future_to_checker[future]
                    results.append(HealthCheckResult(
                        component_name=checker.name,
                        component_type=checker.component_type,
                        status=HealthStatus.CRITICAL,
                        message=f"Health check failed: {str(e)}",
                        response_time_ms=0
                    ))
        
        # Determine overall system health
        overall_status = self._determine_overall_status(results)
        
        system_health = SystemHealth(
            overall_status=overall_status,
            component_results=results
        )
        
        # Store in history
        self._add_to_history(system_health)
        
        return system_health
    
    def _determine_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall system health status."""
        if not results:
            return HealthStatus.UNKNOWN
        
        critical_count = sum(1 for r in results if r.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for r in results if r.status == HealthStatus.WARNING)
        
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _add_to_history(self, system_health: SystemHealth):
        """Add system health to history."""
        self.health_history.append(system_health)
        
        # Limit history size
        if len(self.health_history) > self.max_history_size:
            self.health_history = self.health_history[-self.max_history_size:]
    
    def start_monitoring(self):
        """Start continuous health monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        self.logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop continuous health monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        self.logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                system_health = self.check_system_health()
                
                # Handle unhealthy components
                for result in system_health.get_unhealthy_components():
                    self._handle_unhealthy_component(result)
                
                # Log system status
                if system_health.overall_status != HealthStatus.HEALTHY:
                    self.logger.warning(f"System health: {system_health.overall_status.value}")
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
            
            # Wait for next check
            time.sleep(self.check_interval)
    
    def _handle_unhealthy_component(self, result: HealthCheckResult):
        """Handle an unhealthy component."""
        self.logger.warning(f"Unhealthy component detected: {result.component_name} - {result.message}")
        
        # Attempt recovery for critical components
        if result.is_critical():
            recovery_success = self.service_recovery.attempt_recovery(result)
            if not recovery_success:
                self.logger.error(f"Failed to recover critical component: {result.component_name}")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of system health."""
        if not self.health_history:
            return {"status": "no_data", "message": "No health data available"}
        
        latest_health = self.health_history[-1]
        
        summary = {
            "overall_status": latest_health.overall_status.value,
            "timestamp": latest_health.timestamp.isoformat(),
            "components": {}
        }
        
        for result in latest_health.component_results:
            summary["components"][result.component_name] = {
                "status": result.status.value,
                "message": result.message,
                "response_time_ms": result.response_time_ms,
                "metadata": result.metadata
            }
        
        return summary
    
    def cleanup(self):
        """Cleanup resources."""
        self.stop_monitoring()
        
        # Close all connection pools
        for pool in self.connection_pools.values():
            pool.close_all()


# Global health monitor instance
health_monitor = HealthMonitor()


# Convenience functions for common health checks
def create_database_health_checker(name: str, db_path: str) -> DatabaseHealthChecker:
    """Create a database health checker."""
    return DatabaseHealthChecker(name, db_path)


def create_ollama_health_checker(base_url: str = "http://localhost:11434") -> ExternalServiceHealthChecker:
    """Create an Ollama service health checker."""
    return ExternalServiceHealthChecker("ollama", f"{base_url}/api/tags")


def create_file_system_health_checker(path: str, min_free_space_mb: float = 100.0) -> FileSystemHealthChecker:
    """Create a file system health checker."""
    return FileSystemHealthChecker("file_system", path, min_free_space_mb)


def setup_default_health_monitoring(
    db_path: str = "chroma/chroma.sqlite3",
    data_path: str = "data",
    ollama_url: str = "http://localhost:11434"
):
    """Set up default health monitoring for the RAG system."""
    # Add health checkers
    health_monitor.add_health_checker(create_database_health_checker("chroma_db", db_path))
    health_monitor.add_health_checker(create_ollama_health_checker(ollama_url))
    health_monitor.add_health_checker(create_file_system_health_checker(data_path))
    health_monitor.add_health_checker(MemoryHealthChecker())
    health_monitor.add_health_checker(CPUHealthChecker())
    
    # Add connection pool
    health_monitor.add_connection_pool("chroma", db_path)
    
    # Register recovery strategies
    def restart_ollama_recovery(health_result: HealthCheckResult) -> bool:
        """Recovery strategy for Ollama service."""
        # In a real implementation, this could restart the service
        # For now, just log the attempt
        logging.info("Attempting to recover Ollama service...")
        return False  # Placeholder - actual implementation would restart service
    
    def cleanup_disk_space_recovery(health_result: HealthCheckResult) -> bool:
        """Recovery strategy for disk space issues."""
        # In a real implementation, this could clean up temporary files
        logging.info("Attempting to free disk space...")
        return False  # Placeholder - actual implementation would clean up files
    
    health_monitor.register_recovery_strategy("ollama", restart_ollama_recovery)
    health_monitor.register_recovery_strategy("file_system", cleanup_disk_space_recovery)
    
    return health_monitor