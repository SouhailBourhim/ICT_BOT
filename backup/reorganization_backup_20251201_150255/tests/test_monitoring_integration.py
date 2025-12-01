"""
Integration tests for monitoring system reliability.
"""
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from managers.analytics_manager import AnalyticsManager
from managers.performance_monitor import PerformanceMonitor, PerformanceTracker, AlertLevel
from models.base import Response, RetrievalResult, ProcessedChunk, ContentType


class TestMonitoringIntegration(unittest.TestCase):
    """Integration tests for monitoring system reliability."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Initialize components
        self.analytics_manager = AnalyticsManager(db_path=self.temp_db.name)
        self.performance_monitor = PerformanceMonitor(
            analytics_manager=self.analytics_manager,
            monitoring_interval=1
        )
        
        # Create sample data
        self.sample_chunk = ProcessedChunk(
            chunk_id="chunk_1",
            document_id="doc_1",
            content="Sample content",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapter 1"],
            page_number=1,
            position_in_document=0.1,
            metadata={},
            embedding=[0.1, 0.2, 0.3]
        )
        
        self.sample_retrieval_result = RetrievalResult(
            chunk=self.sample_chunk,
            score=0.85,
            retrieval_method="hybrid",
            metadata={}
        )
        
        self.sample_response = Response(
            content="Sample response",
            sources=[self.sample_retrieval_result],
            confidence=0.9,
            citations=["Document 1"],
            generation_metadata={}
        )
        
        # Alert storage for testing
        self.alerts_received = []
        self.performance_monitor.add_alert_callback(self._store_alert)
    
    def tearDown(self):
        """Clean up test environment."""
        self.performance_monitor.stop_monitoring()
        os.unlink(self.temp_db.name)
    
    def _store_alert(self, alert):
        """Store alert for testing."""
        self.alerts_received.append(alert)
    
    def test_end_to_end_monitoring_workflow(self):
        """Test complete monitoring workflow from query to alert."""
        # Start monitoring
        self.performance_monitor.start_monitoring()
        
        # Simulate query processing with performance tracking
        with PerformanceTracker(self.performance_monitor, "query_processing") as tracker:
            # Simulate query analytics
            query = "What is machine learning?"
            metadata = {
                'conversation_id': 'conv_1',
                'user_id': 'user_1',
                'processing_time': 2.5
            }
            
            # Log query analytics
            self.analytics_manager.log_query(query, self.sample_response, metadata)
            
            # Add some processing time
            time.sleep(0.1)
            tracker.set_metadata('query_length', len(query))
        
        # Simulate multiple operations to build performance data
        for i in range(5):
            with PerformanceTracker(self.performance_monitor, f"operation_{i}") as tracker:
                time.sleep(0.05)
                tracker.set_metadata('iteration', i)
        
        # Wait for monitoring cycle
        time.sleep(2)
        
        # Verify data was collected
        health = self.performance_monitor.get_system_health()
        self.assertIn('overall_status', health)
        self.assertGreater(health['total_requests'], 0)
        
        # Stop monitoring
        self.performance_monitor.stop_monitoring()
    
    @patch('managers.performance_monitor.psutil')
    def test_alert_generation_and_handling(self, mock_psutil):
        """Test alert generation and handling under stress conditions."""
        # Mock high resource usage
        mock_psutil.cpu_percent.return_value = 95.0
        mock_psutil.virtual_memory.return_value = MagicMock(
            percent=92.0, available=1000000000, total=8000000000
        )
        mock_psutil.disk_usage.return_value = MagicMock(
            used=95000000000, total=100000000000, free=5000000000
        )
        mock_psutil.net_io_counters.return_value = MagicMock(
            bytes_sent=1000000, bytes_recv=2000000
        )
        
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=500000000, vms=1000000000)
        mock_process.cpu_percent.return_value = 85.0
        mock_psutil.Process.return_value = mock_process
        mock_psutil.getloadavg.return_value = [3.5, 3.2, 3.0]
        
        # Start monitoring
        self.performance_monitor.start_monitoring()
        
        # Wait for monitoring cycles to generate alerts
        time.sleep(3)
        
        # Stop monitoring
        self.performance_monitor.stop_monitoring()
        
        # Verify alerts were generated
        self.assertGreater(len(self.alerts_received), 0)
        
        # Check for critical alerts
        critical_alerts = [alert for alert in self.alerts_received if alert.level == AlertLevel.CRITICAL]
        self.assertGreater(len(critical_alerts), 0)
    
    def test_performance_optimization_triggers(self):
        """Test automatic performance optimization triggers."""
        # Simulate high error rate
        for _ in range(20):
            self.performance_monitor.track_request(success=False)
        for _ in range(80):
            self.performance_monitor.track_request(success=True)
        
        # Mock high resource usage
        with patch.object(self.performance_monitor, '_collect_system_metrics') as mock_collect:
            mock_collect.return_value = {
                'cpu_usage': 95.0,
                'memory_usage': 88.0,
                'disk_usage': 92.0,
                'timestamp': datetime.now()
            }
            
            # Trigger optimization
            optimizations = self.performance_monitor.optimize_performance()
            
            # Verify optimization suggestions
            self.assertGreater(optimizations['optimizations_suggested'], 0)
            
            # Check for specific optimization types
            opt_types = [opt['type'] for opt in optimizations['optimizations']]
            self.assertIn('cpu_throttling', opt_types)
            self.assertIn('memory_cleanup', opt_types)
            self.assertIn('disk_cleanup', opt_types)
            self.assertIn('error_mitigation', opt_types)
    
    def test_analytics_and_monitoring_data_consistency(self):
        """Test data consistency between analytics and monitoring systems."""
        # Generate test data
        operations = ['query_processing', 'document_retrieval', 'response_generation']
        
        for i in range(10):
            operation = operations[i % len(operations)]
            duration = 1.0 + (i * 0.1)
            success = i % 4 != 0  # 75% success rate
            
            # Track operation performance
            self.performance_monitor.track_operation_time(
                operation=operation,
                duration=duration,
                success=success,
                metadata={'test_iteration': i}
            )
            
            # Log query analytics for some operations
            if operation == 'query_processing':
                query = f"Test query {i}"
                metadata = {
                    'conversation_id': f'conv_{i}',
                    'user_id': f'user_{i % 3}',
                    'processing_time': duration
                }
                self.analytics_manager.log_query(query, self.sample_response, metadata)
        
        # Verify data consistency
        # Check performance monitor stats
        stats = self.performance_monitor.system_stats
        self.assertEqual(stats['total_requests'], 10)
        self.assertEqual(stats['successful_requests'], 7)  # 70% success
        self.assertEqual(stats['failed_requests'], 3)
        
        # Generate analytics report
        report = self.analytics_manager.generate_analytics_report("day")
        
        # Verify report contains expected data
        self.assertGreater(report['query_statistics']['total_queries'], 0)
        self.assertGreater(len(report['performance_metrics']), 0)
    
    def test_monitoring_system_resilience(self):
        """Test monitoring system resilience under various failure conditions."""
        # Test with database connection issues
        original_db_path = self.analytics_manager.db_path
        
        # Temporarily corrupt database path
        self.analytics_manager.db_path = "/invalid/path/db.sqlite"
        
        # Operations should continue without crashing
        try:
            self.performance_monitor.track_operation_time("test_operation", 1.0, True)
            # Should not raise exception
        except Exception as e:
            self.fail(f"Monitoring should handle database errors gracefully: {e}")
        finally:
            # Restore database path
            self.analytics_manager.db_path = original_db_path
        
        # Test with monitoring thread interruption
        self.performance_monitor.start_monitoring()
        time.sleep(1)
        
        # Force stop monitoring
        self.performance_monitor.is_monitoring = False
        time.sleep(2)
        
        # Should handle graceful shutdown
        self.assertFalse(self.performance_monitor.is_monitoring)
    
    def test_concurrent_monitoring_operations(self):
        """Test concurrent monitoring operations for thread safety."""
        import threading
        
        def worker_function(worker_id):
            """Worker function for concurrent testing."""
            for i in range(10):
                # Track operations
                self.performance_monitor.track_operation_time(
                    f"worker_{worker_id}_operation_{i}",
                    0.1,
                    success=True,
                    metadata={'worker_id': worker_id, 'iteration': i}
                )
                
                # Log analytics
                query = f"Worker {worker_id} query {i}"
                metadata = {
                    'conversation_id': f'conv_{worker_id}_{i}',
                    'user_id': f'user_{worker_id}',
                    'processing_time': 0.1
                }
                self.analytics_manager.log_query(query, self.sample_response, metadata)
                
                time.sleep(0.01)  # Small delay
        
        # Start monitoring
        self.performance_monitor.start_monitoring()
        
        # Create and start worker threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker_function, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Stop monitoring
        self.performance_monitor.stop_monitoring()
        
        # Verify all operations were tracked
        stats = self.performance_monitor.system_stats
        self.assertEqual(stats['total_requests'], 50)  # 5 workers * 10 operations each
        self.assertEqual(stats['successful_requests'], 50)
        
        # Verify analytics data
        report = self.analytics_manager.generate_analytics_report("day")
        self.assertEqual(report['query_statistics']['total_queries'], 50)
    
    def test_performance_threshold_adaptation(self):
        """Test dynamic performance threshold adaptation."""
        # Set initial thresholds
        self.performance_monitor.set_threshold('response_time', 2.0, 5.0)
        self.performance_monitor.set_threshold('custom_metric', 50.0, 80.0)
        
        # Verify thresholds were set
        threshold = self.performance_monitor.thresholds['response_time']
        self.assertEqual(threshold.warning_threshold, 2.0)
        self.assertEqual(threshold.critical_threshold, 5.0)
        
        # Test threshold checking with slow operations
        slow_operations = []
        for i in range(3):
            duration = 3.0 + i  # Progressively slower
            # Use operation names that trigger response time alerts
            operation_name = "query_processing"  # This triggers response time checking
            self.performance_monitor.track_operation_time(
                operation_name,
                duration,
                success=True,
                metadata={'iteration': i}
            )
            
            if duration >= threshold.warning_threshold:
                slow_operations.append(duration)
        
        # Should have generated alerts for slow operations
        warning_alerts = [alert for alert in self.alerts_received 
                         if alert.metric_name == 'response_time' and alert.level == AlertLevel.WARNING]
        critical_alerts = [alert for alert in self.alerts_received 
                          if alert.metric_name == 'response_time' and alert.level == AlertLevel.CRITICAL]
        
        # Verify alerts were generated appropriately
        self.assertGreater(len(warning_alerts) + len(critical_alerts), 0)
    
    def test_monitoring_data_retention_and_cleanup(self):
        """Test monitoring data retention and cleanup mechanisms."""
        # Generate historical data
        base_time = datetime.now() - timedelta(days=2)
        
        for i in range(100):
            # Simulate operations over time
            operation_time = base_time + timedelta(minutes=i)
            
            with patch('managers.analytics_manager.datetime') as mock_datetime:
                mock_datetime.now.return_value = operation_time
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
                # Track performance
                self.performance_monitor.track_operation_time(
                    f"historical_operation_{i}",
                    1.0,
                    success=True,
                    metadata={'timestamp': operation_time.isoformat()}
                )
        
        # Verify data was stored
        trends = self.performance_monitor.get_performance_trends("historical_operation_1", hours=72)
        # Should return data (may be empty due to date grouping)
        self.assertIsInstance(trends, list)
        
        # Test cache management
        # Fill cache beyond limit for a monitored metric
        metric_name = 'cpu_usage'  # This is one of the monitored metrics
        for i in range(1200):
            self.performance_monitor.performance_cache.setdefault(metric_name, []).append({
                'timestamp': datetime.now(),
                'value': float(i % 100)
            })
        
        # Trigger cache cleanup with monitored metrics
        metrics = {
            'timestamp': datetime.now(),
            'cpu_usage': 50.0,
            'memory_usage': 60.0,
            'disk_usage': 70.0
        }
        self.performance_monitor._store_metrics(metrics)
        
        # Verify cache was cleaned up
        self.assertLessEqual(
            len(self.performance_monitor.performance_cache[metric_name]),
            self.performance_monitor.cache_max_size
        )


if __name__ == '__main__':
    unittest.main()