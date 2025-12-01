"""
Unit tests for performance monitor.
"""
import os
import tempfile
import time
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.managers.performance_monitor import (
    PerformanceMonitor, PerformanceTracker, AlertLevel, 
    PerformanceThreshold, Alert, default_alert_handler
)
from src.managers.analytics_manager import AnalyticsManager


class TestPerformanceMonitor(unittest.TestCase):
    """Test cases for PerformanceMonitor."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary database for analytics
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.analytics_manager = AnalyticsManager(db_path=self.temp_db.name)
        self.performance_monitor = PerformanceMonitor(
            analytics_manager=self.analytics_manager,
            monitoring_interval=1  # Short interval for testing
        )
        
        # Mock alert callback
        self.alert_callback = MagicMock()
        self.performance_monitor.add_alert_callback(self.alert_callback)
    
    def tearDown(self):
        """Clean up test environment."""
        self.performance_monitor.stop_monitoring()
        os.unlink(self.temp_db.name)
    
    def test_threshold_configuration(self):
        """Test performance threshold configuration."""
        # Test default thresholds
        self.assertIn('response_time', self.performance_monitor.thresholds)
        self.assertIn('memory_usage', self.performance_monitor.thresholds)
        self.assertIn('cpu_usage', self.performance_monitor.thresholds)
        
        # Test custom threshold setting
        self.performance_monitor.set_threshold('custom_metric', 50.0, 80.0, 120)
        
        threshold = self.performance_monitor.thresholds['custom_metric']
        self.assertEqual(threshold.warning_threshold, 50.0)
        self.assertEqual(threshold.critical_threshold, 80.0)
        self.assertEqual(threshold.duration_seconds, 120)
    
    def test_alert_callback_registration(self):
        """Test alert callback registration."""
        callback_count = len(self.performance_monitor.alert_callbacks)
        
        new_callback = MagicMock()
        self.performance_monitor.add_alert_callback(new_callback)
        
        self.assertEqual(len(self.performance_monitor.alert_callbacks), callback_count + 1)
        self.assertIn(new_callback, self.performance_monitor.alert_callbacks)
    
    @patch('src.managers.performance_monitor.psutil')
    def test_system_metrics_collection(self, mock_psutil):
        """Test system metrics collection."""
        # Mock psutil functions
        mock_psutil.cpu_percent.return_value = 45.0
        mock_psutil.virtual_memory.return_value = MagicMock(percent=60.0, available=4000000000, total=8000000000)
        mock_psutil.disk_usage.return_value = MagicMock(used=50000000000, total=100000000000, free=50000000000)
        mock_psutil.net_io_counters.return_value = MagicMock(bytes_sent=1000000, bytes_recv=2000000)
        
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=100000000, vms=200000000)
        mock_process.cpu_percent.return_value = 25.0
        mock_psutil.Process.return_value = mock_process
        
        mock_psutil.getloadavg.return_value = [1.5, 1.2, 1.0]
        
        # Collect metrics
        metrics = self.performance_monitor._collect_system_metrics()
        
        # Verify metrics
        self.assertIn('cpu_usage', metrics)
        self.assertIn('memory_usage', metrics)
        self.assertIn('disk_usage', metrics)
        self.assertEqual(metrics['cpu_usage'], 45.0)
        self.assertEqual(metrics['memory_usage'], 60.0)
    
    def test_request_tracking(self):
        """Test request tracking functionality."""
        initial_total = self.performance_monitor.system_stats['total_requests']
        initial_success = self.performance_monitor.system_stats['successful_requests']
        initial_failed = self.performance_monitor.system_stats['failed_requests']
        
        # Track successful request
        self.performance_monitor.track_request(success=True)
        
        self.assertEqual(self.performance_monitor.system_stats['total_requests'], initial_total + 1)
        self.assertEqual(self.performance_monitor.system_stats['successful_requests'], initial_success + 1)
        self.assertEqual(self.performance_monitor.system_stats['failed_requests'], initial_failed)
        
        # Track failed request
        self.performance_monitor.track_request(success=False)
        
        self.assertEqual(self.performance_monitor.system_stats['total_requests'], initial_total + 2)
        self.assertEqual(self.performance_monitor.system_stats['successful_requests'], initial_success + 1)
        self.assertEqual(self.performance_monitor.system_stats['failed_requests'], initial_failed + 1)
    
    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        # Reset stats
        self.performance_monitor.system_stats = {
            'start_time': datetime.now(),
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0
        }
        
        # Test with no requests
        error_rate = self.performance_monitor._calculate_error_rate()
        self.assertEqual(error_rate, 0.0)
        
        # Add some requests
        for _ in range(8):
            self.performance_monitor.track_request(success=True)
        for _ in range(2):
            self.performance_monitor.track_request(success=False)
        
        error_rate = self.performance_monitor._calculate_error_rate()
        self.assertEqual(error_rate, 20.0)  # 2 failed out of 10 total = 20%
    
    def test_operation_time_tracking(self):
        """Test operation time tracking."""
        operation = "test_operation"
        duration = 2.5
        metadata = {'test_key': 'test_value'}
        
        # Track operation
        self.performance_monitor.track_operation_time(
            operation=operation,
            duration=duration,
            success=True,
            metadata=metadata
        )
        
        # Verify request was tracked
        self.assertGreater(self.performance_monitor.system_stats['total_requests'], 0)
        self.assertGreater(self.performance_monitor.system_stats['successful_requests'], 0)
    
    def test_alert_generation(self):
        """Test alert generation."""
        # Generate a warning alert
        self.performance_monitor._generate_alert(
            AlertLevel.WARNING,
            'test_metric',
            75.0,
            70.0,
            'Test warning message'
        )
        
        # Verify callback was called
        self.alert_callback.assert_called_once()
        
        # Get the alert from the callback
        alert = self.alert_callback.call_args[0][0]
        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertEqual(alert.metric_name, 'test_metric')
        self.assertEqual(alert.current_value, 75.0)
        self.assertEqual(alert.threshold_value, 70.0)
    
    @patch('src.managers.performance_monitor.psutil')
    def test_threshold_checking(self, mock_psutil):
        """Test threshold checking and alert generation."""
        # Mock high CPU usage
        mock_psutil.cpu_percent.return_value = 95.0
        mock_psutil.virtual_memory.return_value = MagicMock(percent=60.0, available=4000000000, total=8000000000)
        mock_psutil.disk_usage.return_value = MagicMock(used=50000000000, total=100000000000, free=50000000000)
        mock_psutil.net_io_counters.return_value = MagicMock(bytes_sent=1000000, bytes_recv=2000000)
        
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=100000000, vms=200000000)
        mock_process.cpu_percent.return_value = 25.0
        mock_psutil.Process.return_value = mock_process
        
        mock_psutil.getloadavg.return_value = [1.5, 1.2, 1.0]
        
        # Collect metrics and check thresholds
        metrics = self.performance_monitor._collect_system_metrics()
        self.performance_monitor._check_thresholds(metrics)
        
        # Should generate critical alert for CPU usage
        self.alert_callback.assert_called()
        alert = self.alert_callback.call_args[0][0]
        self.assertEqual(alert.level, AlertLevel.CRITICAL)
        self.assertEqual(alert.metric_name, 'cpu_usage')
    
    @patch('src.managers.performance_monitor.psutil')
    def test_system_health_status(self, mock_psutil):
        """Test system health status reporting."""
        # Mock normal system metrics
        mock_psutil.cpu_percent.return_value = 45.0
        mock_psutil.virtual_memory.return_value = MagicMock(percent=60.0, available=4000000000, total=8000000000)
        mock_psutil.disk_usage.return_value = MagicMock(used=50000000000, total=100000000000, free=50000000000)
        mock_psutil.net_io_counters.return_value = MagicMock(bytes_sent=1000000, bytes_recv=2000000)
        
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=100000000, vms=200000000)
        mock_process.cpu_percent.return_value = 25.0
        mock_psutil.Process.return_value = mock_process
        
        mock_psutil.getloadavg.return_value = [1.5, 1.2, 1.0]
        
        # Get health status
        health = self.performance_monitor.get_system_health()
        
        # Verify health status
        self.assertIn('overall_status', health)
        self.assertIn('health_scores', health)
        self.assertIn('current_metrics', health)
        self.assertEqual(health['overall_status'], 'healthy')
    
    def test_performance_optimization_suggestions(self):
        """Test performance optimization suggestions."""
        # Mock high resource usage
        with patch.object(self.performance_monitor, '_collect_system_metrics') as mock_collect:
            mock_collect.return_value = {
                'cpu_usage': 95.0,
                'memory_usage': 90.0,
                'disk_usage': 95.0
            }
            
            # Add some failed requests to increase error rate
            for _ in range(15):
                self.performance_monitor.track_request(success=False)
            for _ in range(85):
                self.performance_monitor.track_request(success=True)
            
            optimizations = self.performance_monitor.optimize_performance()
            
            # Should suggest multiple optimizations
            self.assertGreater(optimizations['optimizations_suggested'], 0)
            self.assertIn('optimizations', optimizations)
            
            # Check for specific optimization types
            opt_types = [opt['type'] for opt in optimizations['optimizations']]
            self.assertIn('cpu_throttling', opt_types)
            self.assertIn('memory_cleanup', opt_types)
            self.assertIn('disk_cleanup', opt_types)
            self.assertIn('error_mitigation', opt_types)
    
    def test_monitoring_start_stop(self):
        """Test monitoring start and stop functionality."""
        # Initially not monitoring
        self.assertFalse(self.performance_monitor.is_monitoring)
        
        # Start monitoring
        self.performance_monitor.start_monitoring()
        self.assertTrue(self.performance_monitor.is_monitoring)
        self.assertIsNotNone(self.performance_monitor.monitor_thread)
        
        # Stop monitoring
        self.performance_monitor.stop_monitoring()
        self.assertFalse(self.performance_monitor.is_monitoring)
    
    def test_performance_tracker_context_manager(self):
        """Test PerformanceTracker context manager."""
        operation = "test_operation"
        metadata = {'test': 'value'}
        
        # Test successful operation
        with PerformanceTracker(self.performance_monitor, operation, metadata) as tracker:
            time.sleep(0.1)  # Simulate work
            tracker.set_metadata('additional', 'data')
        
        # Verify request was tracked as successful
        self.assertGreater(self.performance_monitor.system_stats['successful_requests'], 0)
        
        # Test failed operation
        initial_failed = self.performance_monitor.system_stats['failed_requests']
        
        try:
            with PerformanceTracker(self.performance_monitor, operation, metadata) as tracker:
                tracker.mark_failure()
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify request was tracked as failed
        self.assertGreater(self.performance_monitor.system_stats['failed_requests'], initial_failed)
    
    def test_default_alert_handler(self):
        """Test default alert handler."""
        alert = Alert(
            alert_id="test_alert",
            level=AlertLevel.WARNING,
            metric_name="test_metric",
            current_value=75.0,
            threshold_value=70.0,
            message="Test alert message",
            timestamp=datetime.now(),
            metadata={}
        )
        
        # Should not raise exception
        default_alert_handler(alert)
    
    def test_performance_cache_management(self):
        """Test performance data cache management."""
        # Add data to cache
        metric_name = 'cpu_usage'
        for i in range(1200):  # Exceed cache limit
            self.performance_monitor.performance_cache.setdefault(metric_name, []).append({
                'timestamp': datetime.now(),
                'value': float(i % 100)
            })
        
        # Simulate cache cleanup during metrics storage
        metrics = {
            'timestamp': datetime.now(),
            'cpu_usage': 50.0,
            'memory_usage': 60.0,
            'disk_usage': 70.0
        }
        
        self.performance_monitor._store_metrics(metrics)
        
        # Cache should be limited to max size
        self.assertLessEqual(
            len(self.performance_monitor.performance_cache[metric_name]),
            self.performance_monitor.cache_max_size
        )
    
    @patch('src.managers.performance_monitor.logger')
    def test_error_handling(self, mock_logger):
        """Test error handling in performance monitoring."""
        # Test with exception in metrics collection
        with patch.object(self.performance_monitor, '_collect_system_metrics') as mock_collect:
            mock_collect.side_effect = Exception("Test error")
            
            # Should not raise exception but log error
            try:
                self.performance_monitor._monitoring_loop()
            except:
                pass  # Expected to handle gracefully
        
        # Test with invalid callback
        def failing_callback(alert):
            raise Exception("Callback error")
        
        self.performance_monitor.add_alert_callback(failing_callback)
        
        # Generate alert - should handle callback error gracefully
        self.performance_monitor._generate_alert(
            AlertLevel.WARNING,
            'test_metric',
            75.0,
            70.0,
            'Test message'
        )
        
        # Should have logged errors
        mock_logger.error.assert_called()
    
    def test_concurrent_monitoring(self):
        """Test concurrent monitoring operations."""
        import threading
        
        def track_operations():
            for i in range(10):
                self.performance_monitor.track_operation_time(
                    f"operation_{i}",
                    0.1,
                    success=True
                )
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=track_operations)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all operations were tracked
        self.assertEqual(self.performance_monitor.system_stats['total_requests'], 30)
        self.assertEqual(self.performance_monitor.system_stats['successful_requests'], 30)


if __name__ == '__main__':
    unittest.main()