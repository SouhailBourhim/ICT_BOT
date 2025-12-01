"""
Load testing scenarios for concurrent user simulation and system stress testing.
"""

import pytest
import time
import threading
import queue
import random
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch

from src.core.system import RAGSystem
from src.managers.conversation_manager import ConversationManager
from src.managers.query_enhancer import QueryEnhancer
from src.retrievers.hybrid_retriever import HybridRetriever
from src.managers.response_manager import ResponseManager


class LoadTestScenarios:
    """Load testing scenario implementations."""
    
    @staticmethod
    def simulate_user_behavior(user_id, num_queries=10, delay_range=(0.5, 3.0)):
        """Simulate realistic user behavior with random delays."""
        results = []
        conversation_manager = ConversationManager()
        
        try:
            # Start user session
            conversation_id = conversation_manager.start_conversation(f"load_user_{user_id}")
            
            # Simulate queries with realistic delays
            queries = [
                "What is wireless communication?",
                "Explain path loss formula",
                "How does QPSK modulation work?",
                "What is the difference between TDMA and CDMA?",
                "Calculate SNR for given parameters",
                "Describe Rayleigh fading channel",
                "What are the advantages of OFDM?",
                "Explain diversity techniques",
                "How to minimize interference?",
                "What is channel capacity?"
            ]
            
            for i in range(num_queries):
                start_time = time.perf_counter()
                
                # Select random query
                query = random.choice(queries)
                
                # Add user message
                conversation_manager.add_message(conversation_id, {
                    'role': 'user',
                    'content': query,
                    'timestamp': time.time()
                })
                
                # Simulate processing time
                processing_time = random.uniform(0.1, 0.5)
                time.sleep(processing_time)
                
                # Add assistant response
                conversation_manager.add_message(conversation_id, {
                    'role': 'assistant',
                    'content': f"Response to: {query}",
                    'timestamp': time.time()
                })
                
                end_time = time.perf_counter()
                
                results.append({
                    'user_id': user_id,
                    'query_index': i,
                    'response_time': end_time - start_time,
                    'success': True
                })
                
                # Random delay between queries
                delay = random.uniform(*delay_range)
                time.sleep(delay)
                
        except Exception as e:
            results.append({
                'user_id': user_id,
                'error': str(e),
                'success': False
            })
        
        return results


class TestLoadTesting:
    """Load testing test cases."""
    
    @pytest.fixture
    def mock_rag_system(self):
        """Mock RAG system for load testing."""
        with patch('chromadb.PersistentClient'):
            system = RAGSystem()
            return system
    
    def test_concurrent_user_load(self, mock_rag_system):
        """Test system performance with concurrent users."""
        num_users = 20
        queries_per_user = 5
        
        results_queue = queue.Queue()
        
        def user_session(user_id):
            """Individual user session."""
            results = LoadTestScenarios.simulate_user_behavior(
                user_id, 
                num_queries=queries_per_user,
                delay_range=(0.1, 0.5)  # Faster for load testing
            )
            results_queue.put(results)
        
        # Start concurrent user sessions
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_session, i) for i in range(num_users)]
            
            # Wait for all sessions to complete
            for future in as_completed(futures, timeout=60):
                try:
                    future.result()
                except Exception as e:
                    print(f"User session failed: {e}")
        
        total_time = time.perf_counter() - start_time
        
        # Collect and analyze results
        all_results = []
        while not results_queue.empty():
            user_results = results_queue.get()
            all_results.extend(user_results)
        
        # Calculate metrics
        successful_queries = [r for r in all_results if r.get('success', False)]
        failed_queries = [r for r in all_results if not r.get('success', True)]
        
        if successful_queries:
            response_times = [r['response_time'] for r in successful_queries]
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
        else:
            avg_response_time = max_response_time = min_response_time = 0
        
        success_rate = len(successful_queries) / len(all_results) if all_results else 0
        throughput = len(successful_queries) / total_time if total_time > 0 else 0
        
        # Performance assertions
        assert success_rate >= 0.95  # At least 95% success rate
        assert avg_response_time < 5.0  # Average response time < 5s
        assert max_response_time < 15.0  # Max response time < 15s
        assert throughput > 1.0  # At least 1 query per second
        
        print(f"Load Test Results:")
        print(f"  Users: {num_users}")
        print(f"  Total queries: {len(all_results)}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Avg response time: {avg_response_time:.3f}s")
        print(f"  Max response time: {max_response_time:.3f}s")
        print(f"  Min response time: {min_response_time:.3f}s")
        print(f"  Throughput: {throughput:.2f} queries/s")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Failed queries: {len(failed_queries)}")
    
    def test_sustained_load_over_time(self, mock_rag_system):
        """Test system performance under sustained load."""
        duration_minutes = 2  # 2 minute test
        users_per_wave = 5
        wave_interval = 10  # seconds
        
        results = []
        start_time = time.perf_counter()
        end_time = start_time + (duration_minutes * 60)
        
        wave_number = 0
        
        while time.perf_counter() < end_time:
            wave_start = time.perf_counter()
            
            # Start a wave of users
            with ThreadPoolExecutor(max_workers=users_per_wave) as executor:
                futures = []
                
                for i in range(users_per_wave):
                    user_id = f"wave_{wave_number}_user_{i}"
                    future = executor.submit(
                        LoadTestScenarios.simulate_user_behavior,
                        user_id,
                        num_queries=3,
                        delay_range=(0.5, 2.0)
                    )
                    futures.append(future)
                
                # Collect results from this wave
                for future in as_completed(futures, timeout=30):
                    try:
                        wave_results = future.result()
                        results.extend(wave_results)
                    except Exception as e:
                        print(f"Wave {wave_number} user failed: {e}")
            
            wave_number += 1
            
            # Wait for next wave
            wave_duration = time.perf_counter() - wave_start
            sleep_time = max(0, wave_interval - wave_duration)
            time.sleep(sleep_time)
        
        total_duration = time.perf_counter() - start_time
        
        # Analyze sustained load results
        successful_queries = [r for r in results if r.get('success', False)]
        
        if successful_queries:
            # Group results by time windows
            window_size = 30  # 30 second windows
            windows = {}
            
            for result in successful_queries:
                window = int((time.perf_counter() - start_time) // window_size)
                if window not in windows:
                    windows[window] = []
                windows[window].append(result['response_time'])
            
            # Check performance consistency across time windows
            window_averages = []
            for window, times in windows.items():
                avg_time = statistics.mean(times)
                window_averages.append(avg_time)
                print(f"Window {window} (30s): {len(times)} queries, {avg_time:.3f}s avg")
            
            # Performance should remain consistent
            if len(window_averages) > 1:
                performance_variance = statistics.stdev(window_averages)
                assert performance_variance < 2.0  # Performance should be stable
        
        success_rate = len(successful_queries) / len(results) if results else 0
        overall_throughput = len(successful_queries) / total_duration
        
        # Sustained load assertions
        assert success_rate >= 0.90  # At least 90% success rate under sustained load
        assert overall_throughput > 0.5  # At least 0.5 queries per second
        
        print(f"Sustained Load Results:")
        print(f"  Duration: {total_duration:.1f}s")
        print(f"  Waves: {wave_number}")
        print(f"  Total queries: {len(results)}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Overall throughput: {overall_throughput:.2f} queries/s")
    
    def test_spike_load_handling(self, mock_rag_system):
        """Test system behavior during traffic spikes."""
        # Normal load phase
        normal_users = 5
        spike_users = 25
        
        results = {'normal': [], 'spike': [], 'recovery': []}
        
        # Phase 1: Normal load
        print("Phase 1: Normal load")
        with ThreadPoolExecutor(max_workers=normal_users) as executor:
            futures = [
                executor.submit(LoadTestScenarios.simulate_user_behavior, i, 3, (1.0, 2.0))
                for i in range(normal_users)
            ]
            
            for future in as_completed(futures):
                try:
                    user_results = future.result()
                    results['normal'].extend(user_results)
                except Exception as e:
                    print(f"Normal phase user failed: {e}")
        
        # Phase 2: Spike load
        print("Phase 2: Spike load")
        spike_start = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=spike_users) as executor:
            futures = [
                executor.submit(LoadTestScenarios.simulate_user_behavior, f"spike_{i}", 2, (0.1, 0.5))
                for i in range(spike_users)
            ]
            
            for future in as_completed(futures, timeout=45):
                try:
                    user_results = future.result()
                    results['spike'].extend(user_results)
                except Exception as e:
                    print(f"Spike phase user failed: {e}")
        
        spike_duration = time.perf_counter() - spike_start
        
        # Phase 3: Recovery phase
        print("Phase 3: Recovery phase")
        with ThreadPoolExecutor(max_workers=normal_users) as executor:
            futures = [
                executor.submit(LoadTestScenarios.simulate_user_behavior, f"recovery_{i}", 3, (1.0, 2.0))
                for i in range(normal_users)
            ]
            
            for future in as_completed(futures):
                try:
                    user_results = future.result()
                    results['recovery'].extend(user_results)
                except Exception as e:
                    print(f"Recovery phase user failed: {e}")
        
        # Analyze spike handling
        for phase, phase_results in results.items():
            successful = [r for r in phase_results if r.get('success', False)]
            success_rate = len(successful) / len(phase_results) if phase_results else 0
            
            if successful:
                avg_response = statistics.mean([r['response_time'] for r in successful])
                max_response = max([r['response_time'] for r in successful])
            else:
                avg_response = max_response = 0
            
            print(f"{phase.capitalize()} phase:")
            print(f"  Queries: {len(phase_results)}")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Avg response: {avg_response:.3f}s")
            print(f"  Max response: {max_response:.3f}s")
            
            # Phase-specific assertions
            if phase == 'normal':
                assert success_rate >= 0.95
                assert avg_response < 3.0
            elif phase == 'spike':
                assert success_rate >= 0.80  # Allow some degradation during spike
                assert avg_response < 10.0  # Responses may be slower but should complete
            elif phase == 'recovery':
                assert success_rate >= 0.90  # Should recover quickly
                assert avg_response < 5.0
    
    def test_memory_leak_detection(self, mock_rag_system):
        """Test for memory leaks under sustained load."""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run sustained operations
        conversation_manager = ConversationManager()
        
        memory_samples = [initial_memory]
        
        for cycle in range(10):
            # Create and use conversations
            conversation_ids = []
            
            for i in range(20):
                conv_id = conversation_manager.start_conversation(f"leak_test_{cycle}_{i}")
                conversation_ids.append(conv_id)
                
                # Add messages
                for j in range(5):
                    conversation_manager.add_message(conv_id, {
                        'role': 'user',
                        'content': f'Message {j} in cycle {cycle}',
                        'timestamp': time.time()
                    })
            
            # Sample memory usage
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            
            print(f"Cycle {cycle}: {current_memory:.2f}MB")
            
            # Small delay between cycles
            time.sleep(0.5)
        
        final_memory = memory_samples[-1]
        memory_growth = final_memory - initial_memory
        
        # Check for excessive memory growth
        assert memory_growth < 200  # Should not grow more than 200MB
        
        # Check for consistent growth (potential leak)
        if len(memory_samples) >= 5:
            recent_growth = memory_samples[-1] - memory_samples[-5]
            assert recent_growth < 50  # Recent growth should be minimal
        
        print(f"Memory leak test:")
        print(f"  Initial: {initial_memory:.2f}MB")
        print(f"  Final: {final_memory:.2f}MB")
        print(f"  Growth: {memory_growth:.2f}MB")
    
    def test_database_connection_pool_stress(self, mock_rag_system):
        """Test database connection handling under stress."""
        conversation_manager = ConversationManager()
        
        def database_stress_worker(worker_id):
            """Worker that performs database operations."""
            results = []
            
            for i in range(10):
                try:
                    start_time = time.perf_counter()
                    
                    # Create conversation
                    conv_id = conversation_manager.start_conversation(f"db_stress_{worker_id}_{i}")
                    
                    # Add multiple messages
                    for j in range(5):
                        conversation_manager.add_message(conv_id, {
                            'role': 'user',
                            'content': f'DB stress message {j}',
                            'timestamp': time.time()
                        })
                    
                    # Retrieve context
                    context = conversation_manager.get_context(conv_id, max_tokens=1000)
                    
                    end_time = time.perf_counter()
                    
                    results.append({
                        'worker_id': worker_id,
                        'operation': i,
                        'duration': end_time - start_time,
                        'success': True
                    })
                    
                except Exception as e:
                    results.append({
                        'worker_id': worker_id,
                        'operation': i,
                        'error': str(e),
                        'success': False
                    })
            
            return results
        
        # Run concurrent database operations
        num_workers = 15
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(database_stress_worker, i) for i in range(num_workers)]
            
            all_results = []
            for future in as_completed(futures, timeout=60):
                try:
                    worker_results = future.result()
                    all_results.extend(worker_results)
                except Exception as e:
                    print(f"Database stress worker failed: {e}")
        
        # Analyze database stress results
        successful_ops = [r for r in all_results if r.get('success', False)]
        failed_ops = [r for r in all_results if not r.get('success', True)]
        
        success_rate = len(successful_ops) / len(all_results) if all_results else 0
        
        if successful_ops:
            avg_duration = statistics.mean([r['duration'] for r in successful_ops])
            max_duration = max([r['duration'] for r in successful_ops])
        else:
            avg_duration = max_duration = 0
        
        # Database stress assertions
        assert success_rate >= 0.95  # High success rate for database operations
        assert avg_duration < 2.0  # Database operations should be fast
        assert len(failed_ops) < 5  # Minimal failures allowed
        
        print(f"Database stress test:")
        print(f"  Total operations: {len(all_results)}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Avg duration: {avg_duration:.3f}s")
        print(f"  Max duration: {max_duration:.3f}s")
        print(f"  Failed operations: {len(failed_ops)}")