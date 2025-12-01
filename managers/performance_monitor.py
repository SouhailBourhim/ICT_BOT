"""
Performance monitoring and alerting system.
"""
import psutil
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from config.logging_config import get_logger
from managers.analytics_manager import AnalyticsManager

logger = get_logger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    duration_seconds: int = 60  # Time window for threshold evaluation


@dataclass
class Alert:
    """Performance alert."""
    alert_id: str
    level: AlertLevel
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]


class PerformanceMonitor:
    """Performance monitoring and alerting system."""
    
    def __init__(self, analytics_manager: AnalyticsManager, 
                 monitoring_interval: int = 30):
        """Initialize performance monitor."""
        self.analytics_manager = analytics_manager
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Performance thresholds
        self.thresholds = {
            'response_time': PerformanceThreshold(
                metric_name='response_time',
                warning_threshold=5.0,  # 5 seconds
                critical_threshold=10.0  # 10 seconds
            ),
            'memory_usage': PerformanceThreshold(
                metric_name='memory_usage',
                warning_threshold=80.0,  # 80% memory usage
                critical_threshold=90.0  # 90% memory usage
            ),
            'cpu_usage': PerformanceThreshold(
                metric_name='cpu_usage',
                warning_threshold=80.0,  # 80% CPU usage
                critical_threshold=95.0  # 95% CPU usage
            ),
            'disk_usage': PerformanceThreshold(
                metric_name='disk_usage',
                warning_threshold=85.0,  # 85% disk usage
                critical_threshold=95.0  # 95% disk usage
            ),
            'error_rate': PerformanceThreshold(
                metric_name='error_rate',
                warning_threshold=5.0,  # 5% error rate
                critical_threshold=10.0  # 10% error rate
            )
        }
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Performance data cache
        self.performance_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.cache_max_size = 1000
        
        # System resource monitoring
        self.system_stats = {
            'start_time': datetime.now(),
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0
        }
    
    def add_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add alert callback function."""
        self.alert_callbacks.append(callback)
    
    def set_threshold(self, metric_name: str, warning: float, critical: float, 
                     duration: int = 60) -> None:
        """Set performance threshold for a metric."""
        self.thresholds[metric_name] = PerformanceThreshold(
            metric_name=metric_name,
            warning_threshold=warning,
            critical_threshold=critical,
            duration_seconds=duration
        )
        logger.info(f"Updated threshold for {metric_name}: warning={warning}, critical={critical}")
    
    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self.is_monitoring:
            logger.warning("Performance monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()
                
                # Store metrics
                self._store_metrics(system_metrics)
                
                # Check thresholds and generate alerts
                self._check_thresholds(system_metrics)
                
                # Sleep until next monitoring cycle
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            metrics = {
                'timestamp': datetime.now(),
                'cpu_usage': cpu_percent,
                'memory_usage': memory_percent,
                'disk_usage': disk_percent,
                'memory_available': memory.available,
                'memory_total': memory.total,
                'disk_free': disk.free,
                'disk_total': disk.total,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'process_memory_rss': process_memory.rss,
                'process_memory_vms': process_memory.vms,
                'process_cpu_percent': process_cpu,
                'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    def _store_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store metrics in analytics system and cache."""
        try:
            # Store in analytics database
            self.analytics_manager.track_performance(
                operation="system_monitoring",
                duration=0.0,  # Not applicable for system metrics
                metadata=metrics
            )
            
            # Store in cache for threshold checking
            timestamp = metrics['timestamp']
            for metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
                if metric_name not in self.performance_cache:
                    self.performance_cache[metric_name] = []
                
                self.performance_cache[metric_name].append({
                    'timestamp': timestamp,
                    'value': metrics.get(metric_name, 0.0)
                })
                
                # Limit cache size
                if len(self.performance_cache[metric_name]) > self.cache_max_size:
                    self.performance_cache[metric_name] = self.performance_cache[metric_name][-self.cache_max_size:]
            
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
    
    def _check_thresholds(self, current_metrics: Dict[str, Any]) -> None:
        """Check performance thresholds and generate alerts."""
        try:
            for metric_name, threshold in self.thresholds.items():
                if metric_name in current_metrics:
                    current_value = current_metrics[metric_name]
                    
                    # Check critical threshold
                    if current_value >= threshold.critical_threshold:
                        self._generate_alert(
                            AlertLevel.CRITICAL,
                            metric_name,
                            current_value,
                            threshold.critical_threshold,
                            f"Critical {metric_name} threshold exceeded: {current_value:.2f}%"
                        )
                    
                    # Check warning threshold
                    elif current_value >= threshold.warning_threshold:
                        self._generate_alert(
                            AlertLevel.WARNING,
                            metric_name,
                            current_value,
                            threshold.warning_threshold,
                            f"Warning {metric_name} threshold exceeded: {current_value:.2f}%"
                        )
                
                # Check derived metrics
                elif metric_name == 'error_rate':
                    error_rate = self._calculate_error_rate()
                    if error_rate >= threshold.critical_threshold:
                        self._generate_alert(
                            AlertLevel.CRITICAL,
                            metric_name,
                            error_rate,
                            threshold.critical_threshold,
                            f"Critical error rate: {error_rate:.2f}%"
                        )
                    elif error_rate >= threshold.warning_threshold:
                        self._generate_alert(
                            AlertLevel.WARNING,
                            metric_name,
                            error_rate,
                            threshold.warning_threshold,
                            f"High error rate: {error_rate:.2f}%"
                        )
            
        except Exception as e:
            logger.error(f"Failed to check thresholds: {e}")
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate."""
        try:
            total_requests = self.system_stats['total_requests']
            failed_requests = self.system_stats['failed_requests']
            
            if total_requests == 0:
                return 0.0
            
            return (failed_requests / total_requests) * 100
            
        except Exception as e:
            logger.error(f"Failed to calculate error rate: {e}")
            return 0.0
    
    def _generate_alert(self, level: AlertLevel, metric_name: str, 
                       current_value: float, threshold_value: float, 
                       message: str) -> None:
        """Generate and dispatch alert."""
        try:
            alert = Alert(
                alert_id=f"{metric_name}_{int(time.time())}",
                level=level,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=threshold_value,
                message=message,
                timestamp=datetime.now(),
                metadata={
                    'system_stats': self.system_stats.copy(),
                    'monitoring_interval': self.monitoring_interval
                }
            )
            
            # Log alert
            log_level = logger.critical if level == AlertLevel.CRITICAL else logger.warning
            log_level(f"Performance Alert [{level.value.upper()}]: {message}")
            
            # Dispatch to callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
            
        except Exception as e:
            logger.error(f"Failed to generate alert: {e}")
    
    def track_request(self, success: bool = True) -> None:
        """Track request for error rate calculation."""
        self.system_stats['total_requests'] += 1
        if success:
            self.system_stats['successful_requests'] += 1
        else:
            self.system_stats['failed_requests'] += 1
    
    def track_operation_time(self, operation: str, duration: float, 
                           success: bool = True, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Track operation performance."""
        try:
            # Update request stats
            self.track_request(success)
            
            # Store performance data
            performance_metadata = {
                'success': success,
                'operation_type': operation,
                **(metadata or {})
            }
            
            self.analytics_manager.track_performance(
                operation=operation,
                duration=duration,
                metadata=performance_metadata
            )
            
            # Check response time threshold
            if operation in ['query_processing', 'document_retrieval', 'response_generation']:
                threshold = self.thresholds.get('response_time')
                if threshold and duration >= threshold.warning_threshold:
                    level = AlertLevel.CRITICAL if duration >= threshold.critical_threshold else AlertLevel.WARNING
                    self._generate_alert(
                        level,
                        'response_time',
                        duration,
                        threshold.warning_threshold if level == AlertLevel.WARNING else threshold.critical_threshold,
                        f"Slow {operation}: {duration:.2f}s"
                    )
            
        except Exception as e:
            logger.error(f"Failed to track operation time: {e}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        try:
            current_metrics = self._collect_system_metrics()
            
            # Calculate health scores
            health_scores = {}
            for metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
                if metric_name in current_metrics:
                    value = current_metrics[metric_name]
                    threshold = self.thresholds.get(metric_name)
                    
                    if threshold:
                        if value >= threshold.critical_threshold:
                            health_scores[metric_name] = 'critical'
                        elif value >= threshold.warning_threshold:
                            health_scores[metric_name] = 'warning'
                        else:
                            health_scores[metric_name] = 'healthy'
                    else:
                        health_scores[metric_name] = 'unknown'
            
            # Overall health status
            if 'critical' in health_scores.values():
                overall_status = 'critical'
            elif 'warning' in health_scores.values():
                overall_status = 'warning'
            else:
                overall_status = 'healthy'
            
            # Calculate uptime
            uptime = datetime.now() - self.system_stats['start_time']
            
            # Error rate
            error_rate = self._calculate_error_rate()
            
            return {
                'overall_status': overall_status,
                'health_scores': health_scores,
                'current_metrics': current_metrics,
                'uptime_seconds': uptime.total_seconds(),
                'error_rate': error_rate,
                'total_requests': self.system_stats['total_requests'],
                'successful_requests': self.system_stats['successful_requests'],
                'failed_requests': self.system_stats['failed_requests'],
                'monitoring_active': self.is_monitoring
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {'overall_status': 'unknown', 'error': str(e)}
    
    def get_performance_trends(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance trends for a specific metric."""
        try:
            return self.analytics_manager.get_performance_trends(
                operation="system_monitoring",
                days=hours // 24 or 1
            )
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return []
    
    def optimize_performance(self) -> Dict[str, Any]:
        """Automatic performance optimization triggers."""
        try:
            optimizations = []
            current_metrics = self._collect_system_metrics()
            
            # Memory optimization
            if current_metrics.get('memory_usage', 0) > 85:
                optimizations.append({
                    'type': 'memory_cleanup',
                    'action': 'Clear caches and temporary data',
                    'priority': 'high'
                })
            
            # CPU optimization
            if current_metrics.get('cpu_usage', 0) > 90:
                optimizations.append({
                    'type': 'cpu_throttling',
                    'action': 'Reduce concurrent operations',
                    'priority': 'critical'
                })
            
            # Disk optimization
            if current_metrics.get('disk_usage', 0) > 90:
                optimizations.append({
                    'type': 'disk_cleanup',
                    'action': 'Clean temporary files and logs',
                    'priority': 'high'
                })
            
            # Error rate optimization
            error_rate = self._calculate_error_rate()
            if error_rate > 10:
                optimizations.append({
                    'type': 'error_mitigation',
                    'action': 'Enable circuit breaker and retry logic',
                    'priority': 'critical'
                })
            
            # Log optimization recommendations
            if optimizations:
                logger.warning(f"Performance optimization recommendations: {len(optimizations)} actions suggested")
                for opt in optimizations:
                    logger.info(f"Optimization: {opt['type']} - {opt['action']} (Priority: {opt['priority']})")
            
            return {
                'optimizations_suggested': len(optimizations),
                'optimizations': optimizations,
                'current_metrics': current_metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize performance: {e}")
            return {'error': str(e)}


def default_alert_handler(alert: Alert) -> None:
    """Default alert handler that logs alerts."""
    logger.warning(f"ALERT [{alert.level.value.upper()}] {alert.metric_name}: {alert.message}")


# Context manager for tracking operation performance
class PerformanceTracker:
    """Context manager for tracking operation performance."""
    
    def __init__(self, monitor: PerformanceMonitor, operation: str, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.monitor = monitor
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.success = exc_type is None
            
            self.monitor.track_operation_time(
                operation=self.operation,
                duration=duration,
                success=self.success,
                metadata=self.metadata
            )
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the tracking."""
        self.metadata[key] = value
    
    def mark_failure(self) -> None:
        """Mark the operation as failed."""
        self.success = False