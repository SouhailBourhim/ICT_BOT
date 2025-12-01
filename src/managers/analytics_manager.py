"""
Analytics manager for query and response analytics system.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .interfaces import AnalyticsManagerInterface
from src.models.base import (
    QueryAnalytics, ResponseQualityMetrics, PerformanceMetrics, 
    UserFeedback, Response, QueryIntent
)
from config.logging_config import get_logger

logger = get_logger(__name__)


class AnalyticsManager(AnalyticsManagerInterface):
    """Implementation of analytics management system."""
    
    def __init__(self, db_path: str = "analytics.db"):
        """Initialize analytics manager with database."""
        self.db_path = db_path
        self._init_database()
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for enum and datetime objects."""
        if hasattr(obj, 'value'):  # Enum objects
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _init_database(self) -> None:
        """Initialize analytics database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Query analytics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS query_analytics (
                        query_id TEXT PRIMARY KEY,
                        conversation_id TEXT,
                        user_id TEXT,
                        original_query TEXT,
                        enhanced_query TEXT,
                        query_intent TEXT,
                        timestamp TEXT,
                        processing_time REAL,
                        retrieval_count INTEGER,
                        response_length INTEGER,
                        confidence_score REAL,
                        sources_used TEXT,
                        metadata TEXT
                    )
                """)
                
                # Response quality metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS response_quality_metrics (
                        response_id TEXT PRIMARY KEY,
                        query_id TEXT,
                        relevance_score REAL,
                        accuracy_score REAL,
                        completeness_score REAL,
                        citation_quality REAL,
                        user_satisfaction REAL,
                        feedback_timestamp TEXT,
                        metadata TEXT,
                        FOREIGN KEY (query_id) REFERENCES query_analytics (query_id)
                    )
                """)
                
                # Performance metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        metric_id TEXT PRIMARY KEY,
                        operation TEXT,
                        timestamp TEXT,
                        duration REAL,
                        memory_usage REAL,
                        cpu_usage REAL,
                        success BOOLEAN,
                        error_message TEXT,
                        metadata TEXT
                    )
                """)
                
                # User feedback table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_feedback (
                        feedback_id TEXT PRIMARY KEY,
                        conversation_id TEXT,
                        message_id TEXT,
                        user_id TEXT,
                        rating INTEGER,
                        feedback_type TEXT,
                        comments TEXT,
                        timestamp TEXT,
                        metadata TEXT
                    )
                """)
                
                # Create indexes for better query performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_timestamp ON query_analytics(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_user ON query_analytics(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_operation ON performance_metrics(operation)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_rating ON user_feedback(rating)")
                
                conn.commit()
                logger.info("Analytics database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize analytics database: {e}")
            raise
    
    def log_query(self, query: str, response: Response, metadata: Dict[str, Any]) -> None:
        """Log query and response for analytics."""
        try:
            query_id = str(uuid.uuid4())
            
            # Extract analytics data
            analytics = QueryAnalytics(
                query_id=query_id,
                conversation_id=metadata.get('conversation_id', ''),
                user_id=metadata.get('user_id', ''),
                original_query=query,
                enhanced_query=metadata.get('enhanced_query', query),
                query_intent=metadata.get('query_intent', QueryIntent.FACTUAL),
                timestamp=datetime.now(),
                processing_time=metadata.get('processing_time', 0.0),
                retrieval_count=len(response.sources),
                response_length=len(response.content),
                confidence_score=response.confidence,
                sources_used=[source.chunk.document_id for source in response.sources],
                metadata=metadata
            )
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Serialize metadata with custom encoder for enums
                serialized_metadata = json.dumps(analytics.metadata, default=self._json_serializer)
                
                cursor.execute("""
                    INSERT INTO query_analytics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analytics.query_id,
                    analytics.conversation_id,
                    analytics.user_id,
                    analytics.original_query,
                    analytics.enhanced_query,
                    analytics.query_intent.value,
                    analytics.timestamp.isoformat(),
                    analytics.processing_time,
                    analytics.retrieval_count,
                    analytics.response_length,
                    analytics.confidence_score,
                    json.dumps(analytics.sources_used),
                    serialized_metadata
                ))
                conn.commit()
            
            # Calculate and store response quality metrics
            self._calculate_response_quality(query_id, response, metadata)
            
            logger.debug(f"Logged query analytics for query_id: {query_id}")
            
        except Exception as e:
            logger.error(f"Failed to log query analytics: {e}")
    
    def _calculate_response_quality(self, query_id: str, response: Response, metadata: Dict[str, Any]) -> None:
        """Calculate response quality metrics."""
        try:
            response_id = str(uuid.uuid4())
            
            # Calculate quality scores
            relevance_score = self._calculate_relevance_score(response)
            accuracy_score = self._calculate_accuracy_score(response)
            completeness_score = self._calculate_completeness_score(response)
            citation_quality = self._calculate_citation_quality(response)
            
            metrics = ResponseQualityMetrics(
                response_id=response_id,
                query_id=query_id,
                relevance_score=relevance_score,
                accuracy_score=accuracy_score,
                completeness_score=completeness_score,
                citation_quality=citation_quality,
                user_satisfaction=None,  # Will be updated when feedback is received
                feedback_timestamp=None,
                metadata=metadata
            )
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO response_quality_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.response_id,
                    metrics.query_id,
                    metrics.relevance_score,
                    metrics.accuracy_score,
                    metrics.completeness_score,
                    metrics.citation_quality,
                    metrics.user_satisfaction,
                    metrics.feedback_timestamp,
                    json.dumps(metrics.metadata, default=self._json_serializer)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to calculate response quality metrics: {e}")
    
    def _calculate_relevance_score(self, response: Response) -> float:
        """Calculate relevance score based on source scores and confidence."""
        if not response.sources:
            return 0.0
        
        # Average of source scores weighted by confidence
        source_scores = [source.score for source in response.sources]
        avg_source_score = sum(source_scores) / len(source_scores)
        
        # Combine with response confidence
        relevance_score = (avg_source_score * 0.7) + (response.confidence * 0.3)
        return min(1.0, max(0.0, relevance_score))
    
    def _calculate_accuracy_score(self, response: Response) -> float:
        """Calculate accuracy score based on source quality and citations."""
        if not response.sources:
            return 0.0
        
        # Score based on number of high-quality sources
        high_quality_sources = sum(1 for source in response.sources if source.score > 0.8)
        source_quality_score = high_quality_sources / len(response.sources)
        
        # Score based on citation presence
        citation_score = 1.0 if response.citations else 0.5
        
        return (source_quality_score * 0.8) + (citation_score * 0.2)
    
    def _calculate_completeness_score(self, response: Response) -> float:
        """Calculate completeness score based on response length and source diversity."""
        # Score based on response length (optimal range: 200-800 characters)
        length_score = min(1.0, len(response.content) / 800) if len(response.content) < 800 else 1.0
        if len(response.content) < 100:
            length_score *= 0.5
        
        # Score based on source diversity
        unique_documents = len(set(source.chunk.document_id for source in response.sources))
        diversity_score = min(1.0, unique_documents / 3)  # Optimal: 3+ different documents
        
        return (length_score * 0.6) + (diversity_score * 0.4)
    
    def _calculate_citation_quality(self, response: Response) -> float:
        """Calculate citation quality score."""
        if not response.citations:
            return 0.0
        
        # Score based on citation count relative to sources
        citation_coverage = len(response.citations) / max(1, len(response.sources))
        citation_score = min(1.0, citation_coverage)
        
        # Bonus for detailed citations (page numbers, sections)
        detailed_citations = sum(1 for citation in response.citations 
                               if any(keyword in citation.lower() 
                                     for keyword in ['page', 'section', 'chapter']))
        detail_bonus = min(0.2, detailed_citations * 0.1)
        
        return min(1.0, citation_score + detail_bonus)
    
    def track_performance(self, operation: str, duration: float, metadata: Dict[str, Any]) -> None:
        """Track performance metrics."""
        try:
            metric_id = str(uuid.uuid4())
            
            metrics = PerformanceMetrics(
                metric_id=metric_id,
                operation=operation,
                timestamp=datetime.now(),
                duration=duration,
                memory_usage=metadata.get('memory_usage', 0.0),
                cpu_usage=metadata.get('cpu_usage', 0.0),
                success=metadata.get('success', True),
                error_message=metadata.get('error_message'),
                metadata=metadata
            )
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO performance_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.metric_id,
                    metrics.operation,
                    metrics.timestamp.isoformat(),
                    metrics.duration,
                    metrics.memory_usage,
                    metrics.cpu_usage,
                    metrics.success,
                    metrics.error_message,
                    json.dumps(metrics.metadata, default=self._json_serializer)
                ))
                conn.commit()
                
            logger.debug(f"Tracked performance metric for operation: {operation}")
            
        except Exception as e:
            logger.error(f"Failed to track performance metrics: {e}")
    
    def collect_feedback(self, conversation_id: str, message_id: str, 
                        feedback: Dict[str, Any]) -> None:
        """Collect user feedback."""
        try:
            feedback_id = str(uuid.uuid4())
            
            user_feedback = UserFeedback(
                feedback_id=feedback_id,
                conversation_id=conversation_id,
                message_id=message_id,
                user_id=feedback.get('user_id', ''),
                rating=feedback.get('rating', 0),
                feedback_type=feedback.get('feedback_type', 'general'),
                comments=feedback.get('comments'),
                timestamp=datetime.now(),
                metadata=feedback
            )
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_feedback.feedback_id,
                    user_feedback.conversation_id,
                    user_feedback.message_id,
                    user_feedback.user_id,
                    user_feedback.rating,
                    user_feedback.feedback_type,
                    user_feedback.comments,
                    user_feedback.timestamp.isoformat(),
                    json.dumps(user_feedback.metadata, default=self._json_serializer)
                ))
                conn.commit()
            
            # Update response quality metrics with user satisfaction
            self._update_response_satisfaction(message_id, user_feedback.rating)
            
            logger.debug(f"Collected user feedback: {feedback_id}")
            
        except Exception as e:
            logger.error(f"Failed to collect user feedback: {e}")
    
    def _update_response_satisfaction(self, message_id: str, rating: int) -> None:
        """Update response quality metrics with user satisfaction."""
        try:
            # Convert rating to satisfaction score (1-5 scale to 0-1 scale)
            satisfaction_score = (rating - 1) / 4.0
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Find the query_id associated with this message
                # This is a simplified approach - in practice, you'd need proper message-query mapping
                cursor.execute("""
                    UPDATE response_quality_metrics 
                    SET user_satisfaction = ?, feedback_timestamp = ?
                    WHERE query_id IN (
                        SELECT query_id FROM query_analytics 
                        WHERE conversation_id = (
                            SELECT conversation_id FROM user_feedback 
                            WHERE message_id = ?
                        )
                        ORDER BY timestamp DESC LIMIT 1
                    )
                """, (satisfaction_score, datetime.now().isoformat(), message_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update response satisfaction: {e}")
    
    def generate_analytics_report(self, time_period: str) -> Dict[str, Any]:
        """Generate analytics report for specified time period."""
        try:
            # Calculate time range
            end_time = datetime.now()
            if time_period == "day":
                start_time = end_time - timedelta(days=1)
            elif time_period == "week":
                start_time = end_time - timedelta(weeks=1)
            elif time_period == "month":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=7)  # Default to week
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Query statistics
                cursor.execute("""
                    SELECT COUNT(*), AVG(processing_time), AVG(confidence_score), AVG(response_length)
                    FROM query_analytics 
                    WHERE timestamp >= ? AND timestamp <= ?
                """, (start_time.isoformat(), end_time.isoformat()))
                
                query_stats = cursor.fetchone()
                
                # Response quality statistics
                cursor.execute("""
                    SELECT AVG(relevance_score), AVG(accuracy_score), 
                           AVG(completeness_score), AVG(citation_quality), AVG(user_satisfaction)
                    FROM response_quality_metrics rqm
                    JOIN query_analytics qa ON rqm.query_id = qa.query_id
                    WHERE qa.timestamp >= ? AND qa.timestamp <= ?
                """, (start_time.isoformat(), end_time.isoformat()))
                
                quality_stats = cursor.fetchone()
                
                # Performance statistics
                cursor.execute("""
                    SELECT operation, COUNT(*), AVG(duration), 
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                    FROM performance_metrics 
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY operation
                """, (start_time.isoformat(), end_time.isoformat()))
                
                performance_stats = cursor.fetchall()
                
                # User feedback statistics
                cursor.execute("""
                    SELECT AVG(rating), COUNT(*), feedback_type, COUNT(*) as count
                    FROM user_feedback 
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY feedback_type
                """, (start_time.isoformat(), end_time.isoformat()))
                
                feedback_stats = cursor.fetchall()
                
                # Most common query intents
                cursor.execute("""
                    SELECT query_intent, COUNT(*) as count
                    FROM query_analytics 
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY query_intent
                    ORDER BY count DESC
                """, (start_time.isoformat(), end_time.isoformat()))
                
                intent_stats = cursor.fetchall()
            
            # Compile report
            report = {
                "time_period": time_period,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "query_statistics": {
                    "total_queries": query_stats[0] or 0,
                    "avg_processing_time": query_stats[1] or 0.0,
                    "avg_confidence": query_stats[2] or 0.0,
                    "avg_response_length": query_stats[3] or 0.0
                },
                "quality_metrics": {
                    "avg_relevance": quality_stats[0] or 0.0,
                    "avg_accuracy": quality_stats[1] or 0.0,
                    "avg_completeness": quality_stats[2] or 0.0,
                    "avg_citation_quality": quality_stats[3] or 0.0,
                    "avg_user_satisfaction": quality_stats[4] or 0.0
                },
                "performance_metrics": [
                    {
                        "operation": stat[0],
                        "count": stat[1],
                        "avg_duration": stat[2],
                        "success_rate": stat[3]
                    }
                    for stat in performance_stats
                ],
                "feedback_summary": [
                    {
                        "feedback_type": stat[2],
                        "count": stat[3],
                        "avg_rating": stat[0]
                    }
                    for stat in feedback_stats
                ],
                "query_intents": [
                    {
                        "intent": stat[0],
                        "count": stat[1]
                    }
                    for stat in intent_stats
                ]
            }
            
            logger.info(f"Generated analytics report for {time_period}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate analytics report: {e}")
            return {}
    
    def get_query_patterns(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent query patterns for analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT original_query, enhanced_query, query_intent, 
                           processing_time, confidence_score, timestamp
                    FROM query_analytics 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                patterns = []
                for row in cursor.fetchall():
                    patterns.append({
                        "original_query": row[0],
                        "enhanced_query": row[1],
                        "query_intent": row[2],
                        "processing_time": row[3],
                        "confidence_score": row[4],
                        "timestamp": row[5]
                    })
                
                return patterns
                
        except Exception as e:
            logger.error(f"Failed to get query patterns: {e}")
            return []
    
    def get_performance_trends(self, operation: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get performance trends for specific operation."""
        try:
            start_time = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DATE(timestamp) as date, 
                           AVG(duration) as avg_duration,
                           COUNT(*) as count,
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                    FROM performance_metrics 
                    WHERE operation = ? AND timestamp >= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """, (operation, start_time.isoformat()))
                
                trends = []
                for row in cursor.fetchall():
                    trends.append({
                        "date": row[0],
                        "avg_duration": row[1],
                        "count": row[2],
                        "success_rate": row[3]
                    })
                
                return trends
                
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return []