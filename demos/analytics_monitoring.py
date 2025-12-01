#!/usr/bin/env python3
"""
Demo script for analytics and monitoring systems.
"""
import time
from datetime import datetime
from src.managers.analytics_manager import AnalyticsManager
from src.managers.performance_monitor import PerformanceMonitor, PerformanceTracker
from src.models.base import (
    Response, RetrievalResult, ProcessedChunk, ContentType, QueryIntent
)


def create_sample_data():
    """Create sample data for demonstration."""
    chunk = ProcessedChunk(
        chunk_id="demo_chunk_1",
        document_id="demo_doc_1",
        content="This is a sample chunk about machine learning algorithms.",
        content_type=ContentType.TEXT,
        hierarchical_context=["Chapter 3", "Section 3.1", "Machine Learning Basics"],
        page_number=45,
        position_in_document=0.3,
        metadata={"topic": "machine_learning", "difficulty": "intermediate"},
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
    )
    
    retrieval_result = RetrievalResult(
        chunk=chunk,
        score=0.92,
        retrieval_method="hybrid",
        metadata={"search_type": "semantic_keyword"}
    )
    
    response = Response(
        content="Machine learning algorithms are computational methods that enable systems to learn patterns from data without being explicitly programmed for each specific task.",
        sources=[retrieval_result],
        confidence=0.88,
        citations=["Machine Learning Textbook, Chapter 3, Page 45"],
        generation_metadata={"model": "llama3", "temperature": 0.7}
    )
    
    return response


def demo_analytics_system():
    """Demonstrate analytics system functionality."""
    print("🔍 Analytics System Demo")
    print("=" * 50)
    
    # Initialize analytics manager
    analytics = AnalyticsManager(db_path="demo_analytics.db")
    
    # Create sample response
    response = create_sample_data()
    
    # Log some queries
    queries = [
        ("What is machine learning?", QueryIntent.CONCEPTUAL),
        ("How do neural networks work?", QueryIntent.PROCEDURAL),
        ("Compare supervised vs unsupervised learning", QueryIntent.COMPARATIVE),
        ("Why is my model not converging?", QueryIntent.TROUBLESHOOTING),
        ("What is the accuracy of random forests?", QueryIntent.FACTUAL)
    ]
    
    print("📝 Logging sample queries...")
    for i, (query, intent) in enumerate(queries):
        metadata = {
            'conversation_id': f'demo_conv_{i // 2}',
            'user_id': f'demo_user_{i % 3}',
            'enhanced_query': f"Enhanced: {query}",
            'query_intent': intent,
            'processing_time': 1.5 + (i * 0.3)
        }
        
        analytics.log_query(query, response, metadata)
        print(f"  ✓ Logged: {query[:50]}...")
    
    # Collect some feedback
    print("\n💬 Collecting user feedback...")
    feedback_data = [
        {'rating': 5, 'feedback_type': 'helpful', 'comments': 'Very clear explanation'},
        {'rating': 4, 'feedback_type': 'accurate', 'comments': 'Good but could be more detailed'},
        {'rating': 3, 'feedback_type': 'complete', 'comments': 'Missing some examples'}
    ]
    
    for i, feedback in enumerate(feedback_data):
        feedback['user_id'] = f'demo_user_{i}'
        analytics.collect_feedback(f'demo_conv_{i}', f'msg_{i}', feedback)
        print(f"  ✓ Feedback: {feedback['rating']}/5 - {feedback['feedback_type']}")
    
    # Generate analytics report
    print("\n📊 Generating analytics report...")
    report = analytics.generate_analytics_report("day")
    
    print(f"  📈 Total queries: {report['query_statistics']['total_queries']}")
    print(f"  ⏱️  Avg processing time: {report['query_statistics']['avg_processing_time']:.2f}s")
    print(f"  🎯 Avg confidence: {report['query_statistics']['avg_confidence']:.2f}")
    print(f"  📏 Avg response length: {report['query_statistics']['avg_response_length']:.0f} chars")
    
    print(f"\n  🏆 Quality Metrics:")
    print(f"    Relevance: {report['quality_metrics']['avg_relevance']:.2f}")
    print(f"    Accuracy: {report['quality_metrics']['avg_accuracy']:.2f}")
    print(f"    Completeness: {report['quality_metrics']['avg_completeness']:.2f}")
    print(f"    Citation Quality: {report['quality_metrics']['avg_citation_quality']:.2f}")
    
    if report['quality_metrics']['avg_user_satisfaction']:
        print(f"    User Satisfaction: {report['quality_metrics']['avg_user_satisfaction']:.2f}")
    
    # Get query patterns
    print(f"\n  🔍 Recent Query Patterns:")
    patterns = analytics.get_query_patterns(limit=3)
    for pattern in patterns:
        print(f"    • {pattern['original_query'][:40]}... ({pattern['query_intent']})")
    
    print("\n✅ Analytics demo completed!")
    return analytics


def demo_performance_monitoring(analytics):
    """Demonstrate performance monitoring functionality."""
    print("\n\n⚡ Performance Monitoring Demo")
    print("=" * 50)
    
    # Initialize performance monitor
    monitor = PerformanceMonitor(analytics, monitoring_interval=2)
    
    # Add custom alert handler
    def custom_alert_handler(alert):
        print(f"🚨 ALERT [{alert.level.value.upper()}]: {alert.message}")
    
    monitor.add_alert_callback(custom_alert_handler)
    
    # Set custom thresholds for demo
    monitor.set_threshold('response_time', 2.0, 4.0)
    print("🎛️  Set response time thresholds: Warning=2.0s, Critical=4.0s")
    
    # Start monitoring
    print("🔄 Starting performance monitoring...")
    monitor.start_monitoring()
    
    # Simulate various operations
    print("\n🏃 Simulating system operations...")
    
    operations = [
        ("query_processing", 1.5, True),
        ("document_retrieval", 0.8, True),
        ("response_generation", 2.5, True),  # Should trigger warning
        ("query_processing", 4.5, True),     # Should trigger critical alert
        ("document_retrieval", 1.2, False),  # Failed operation
        ("response_generation", 0.9, True),
    ]
    
    for operation, duration, success in operations:
        print(f"  🔧 Executing {operation} ({duration}s, {'✓' if success else '✗'})")
        
        with PerformanceTracker(monitor, operation) as tracker:
            time.sleep(duration)
            if not success:
                tracker.mark_failure()
            tracker.set_metadata('demo_operation', True)
        
        time.sleep(0.5)  # Brief pause between operations
    
    # Wait for monitoring to collect data
    print("\n⏳ Waiting for monitoring data collection...")
    time.sleep(3)
    
    # Get system health
    print("\n🏥 System Health Status:")
    health = monitor.get_system_health()
    print(f"  Overall Status: {health['overall_status'].upper()}")
    print(f"  Uptime: {health['uptime_seconds']:.1f} seconds")
    print(f"  Total Requests: {health['total_requests']}")
    print(f"  Success Rate: {(health['successful_requests']/max(1, health['total_requests'])*100):.1f}%")
    print(f"  Error Rate: {health['error_rate']:.1f}%")
    
    print(f"\n  Resource Usage:")
    current_metrics = health['current_metrics']
    print(f"    CPU: {current_metrics.get('cpu_usage', 0):.1f}%")
    print(f"    Memory: {current_metrics.get('memory_usage', 0):.1f}%")
    print(f"    Disk: {current_metrics.get('disk_usage', 0):.1f}%")
    
    # Get performance optimization suggestions
    print(f"\n🔧 Performance Optimization Suggestions:")
    optimizations = monitor.optimize_performance()
    if optimizations['optimizations_suggested'] > 0:
        for opt in optimizations['optimizations']:
            priority_emoji = "🔴" if opt['priority'] == 'critical' else "🟡" if opt['priority'] == 'high' else "🟢"
            print(f"    {priority_emoji} {opt['type']}: {opt['action']}")
    else:
        print("    ✅ No optimizations needed - system running well!")
    
    # Stop monitoring
    print("\n🛑 Stopping performance monitoring...")
    monitor.stop_monitoring()
    
    print("✅ Performance monitoring demo completed!")
    return monitor


def demo_integration():
    """Demonstrate integration between analytics and monitoring."""
    print("\n\n🔗 Integration Demo")
    print("=" * 50)
    
    print("🔄 Running integrated workflow simulation...")
    
    # This would typically be integrated into the main RAG system
    # Here we just show how the components work together
    
    analytics = AnalyticsManager(db_path="demo_integration.db")
    monitor = PerformanceMonitor(analytics, monitoring_interval=1)
    
    # Start monitoring
    monitor.start_monitoring()
    
    # Simulate a complete RAG query workflow
    with PerformanceTracker(monitor, "complete_rag_workflow") as tracker:
        print("  1️⃣ Processing user query...")
        time.sleep(0.3)
        tracker.set_metadata('step', 'query_processing')
        
        print("  2️⃣ Retrieving relevant documents...")
        time.sleep(0.5)
        tracker.set_metadata('step', 'document_retrieval')
        
        print("  3️⃣ Generating response...")
        time.sleep(0.4)
        tracker.set_metadata('step', 'response_generation')
        
        # Log the complete interaction
        response = create_sample_data()
        metadata = {
            'conversation_id': 'integration_demo',
            'user_id': 'demo_user',
            'processing_time': 1.2,
            'query_intent': QueryIntent.FACTUAL
        }
        analytics.log_query("How does the RAG system work?", response, metadata)
        
        print("  4️⃣ Logging analytics data...")
        time.sleep(0.1)
    
    # Wait for data collection
    time.sleep(2)
    
    # Show integrated results
    print("\n📊 Integrated Results:")
    
    # Analytics data
    report = analytics.generate_analytics_report("day")
    print(f"  📈 Queries processed: {report['query_statistics']['total_queries']}")
    
    # Performance data
    health = monitor.get_system_health()
    print(f"  ⚡ System health: {health['overall_status']}")
    print(f"  🎯 Success rate: {(health['successful_requests']/max(1, health['total_requests'])*100):.1f}%")
    
    monitor.stop_monitoring()
    print("\n✅ Integration demo completed!")


def main():
    """Run the complete demo."""
    print("🚀 RAG System Analytics & Monitoring Demo")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run analytics demo
        analytics = demo_analytics_system()
        
        # Run performance monitoring demo
        monitor = demo_performance_monitoring(analytics)
        
        # Run integration demo
        demo_integration()
        
        print(f"\n🎉 All demos completed successfully!")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        raise
    finally:
        # Cleanup demo databases
        import os
        for db_file in ["demo_analytics.db", "demo_integration.db"]:
            if os.path.exists(db_file):
                os.unlink(db_file)
                print(f"🧹 Cleaned up {db_file}")


if __name__ == "__main__":
    main()