"""
Database optimization utilities for improved query performance and indexing.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Database optimization and performance tuning utilities."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection_pool_size = 10
        self._connection_pool = []
        self._initialize_optimizations()
    
    def _initialize_optimizations(self):
        """Initialize database optimizations."""
        with self.get_connection() as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            
            # Optimize SQLite settings
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety and performance
            conn.execute("PRAGMA cache_size=10000")    # 10MB cache
            conn.execute("PRAGMA temp_store=MEMORY")   # Use memory for temp tables
            conn.execute("PRAGMA mmap_size=268435456") # 256MB memory map
            
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys=ON")
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get optimized database connection with proper settings."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # 30 second timeout
            check_same_thread=False
        )
        
        # Set connection-specific optimizations
        conn.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout
        conn.row_factory = sqlite3.Row  # Enable column access by name
        
        try:
            yield conn
        finally:
            conn.close()
    
    def create_indexes(self):
        """Create optimized indexes for better query performance."""
        indexes = [
            # Conversation indexes
            """CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
               ON conversations(user_id)""",
            
            """CREATE INDEX IF NOT EXISTS idx_conversations_created_at 
               ON conversations(created_at DESC)""",
            
            """CREATE INDEX IF NOT EXISTS idx_conversations_updated_at 
               ON conversations(updated_at DESC)""",
            
            # Message indexes
            """CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
               ON messages(conversation_id)""",
            
            """CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
               ON messages(timestamp DESC)""",
            
            """CREATE INDEX IF NOT EXISTS idx_messages_role 
               ON messages(role)""",
            
            # Document metadata indexes
            """CREATE INDEX IF NOT EXISTS idx_documents_course_module 
               ON document_metadata(course_module)""",
            
            """CREATE INDEX IF NOT EXISTS idx_documents_document_type 
               ON document_metadata(document_type)""",
            
            """CREATE INDEX IF NOT EXISTS idx_documents_creation_date 
               ON document_metadata(creation_date DESC)""",
            
            # Chunk indexes
            """CREATE INDEX IF NOT EXISTS idx_chunks_document_id 
               ON document_chunks(document_id)""",
            
            """CREATE INDEX IF NOT EXISTS idx_chunks_content_type 
               ON document_chunks(content_type)""",
            
            """CREATE INDEX IF NOT EXISTS idx_chunks_page_number 
               ON document_chunks(page_number)""",
            
            # Analytics indexes
            """CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp 
               ON query_logs(timestamp DESC)""",
            
            """CREATE INDEX IF NOT EXISTS idx_query_logs_user_id 
               ON query_logs(user_id)""",
            
            """CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp 
               ON performance_metrics(timestamp DESC)""",
            
            # Composite indexes for common queries
            """CREATE INDEX IF NOT EXISTS idx_messages_conv_timestamp 
               ON messages(conversation_id, timestamp DESC)""",
            
            """CREATE INDEX IF NOT EXISTS idx_chunks_doc_page 
               ON document_chunks(document_id, page_number)""",
            
            """CREATE INDEX IF NOT EXISTS idx_documents_module_type 
               ON document_metadata(course_module, document_type)"""
        ]
        
        with self.get_connection() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(index_sql)
                    logger.info(f"Created index: {index_sql.split()[5]}")
                except sqlite3.Error as e:
                    logger.warning(f"Failed to create index: {e}")
            
            conn.commit()
    
    def analyze_query_performance(self, query: str, params: tuple = ()) -> Dict[str, Any]:
        """Analyze query performance and provide optimization suggestions."""
        with self.get_connection() as conn:
            # Enable query plan analysis
            conn.execute("PRAGMA query_only=ON")
            
            # Get query plan
            explain_query = f"EXPLAIN QUERY PLAN {query}"
            plan_result = conn.execute(explain_query, params).fetchall()
            
            # Measure execution time
            start_time = time.perf_counter()
            conn.execute("PRAGMA query_only=OFF")
            result = conn.execute(query, params).fetchall()
            execution_time = time.perf_counter() - start_time
            
            # Analyze plan for optimization opportunities
            suggestions = self._analyze_query_plan(plan_result)
            
            return {
                'execution_time': execution_time,
                'query_plan': [dict(row) for row in plan_result],
                'result_count': len(result),
                'optimization_suggestions': suggestions
            }
    
    def _analyze_query_plan(self, plan: List[sqlite3.Row]) -> List[str]:
        """Analyze query plan and provide optimization suggestions."""
        suggestions = []
        
        for row in plan:
            detail = row['detail'].lower()
            
            # Check for table scans
            if 'scan table' in detail and 'using index' not in detail:
                table_name = detail.split('scan table ')[1].split()[0]
                suggestions.append(f"Consider adding index to table '{table_name}'")
            
            # Check for temporary B-trees
            if 'use temp b-tree' in detail:
                suggestions.append("Query uses temporary B-tree - consider adding appropriate index")
            
            # Check for sorting without index
            if 'order by' in detail and 'using index' not in detail:
                suggestions.append("ORDER BY clause not using index - consider adding covering index")
        
        return suggestions
    
    def optimize_database(self):
        """Run comprehensive database optimization."""
        logger.info("Starting database optimization...")
        
        with self.get_connection() as conn:
            # Update table statistics
            conn.execute("ANALYZE")
            
            # Vacuum database to reclaim space and optimize layout
            conn.execute("VACUUM")
            
            # Reindex all indexes
            conn.execute("REINDEX")
            
            conn.commit()
        
        # Create/update indexes
        self.create_indexes()
        
        logger.info("Database optimization completed")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and performance metrics."""
        with self.get_connection() as conn:
            stats = {}
            
            # Database size
            stats['database_size_mb'] = Path(self.db_path).stat().st_size / (1024 * 1024)
            
            # Table statistics
            tables_query = """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
            tables = [row[0] for row in conn.execute(tables_query).fetchall()]
            
            stats['tables'] = {}
            for table in tables:
                count_query = f"SELECT COUNT(*) FROM {table}"
                count = conn.execute(count_query).fetchone()[0]
                stats['tables'][table] = {'row_count': count}
            
            # Index statistics
            indexes_query = """
                SELECT name, tbl_name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """
            indexes = conn.execute(indexes_query).fetchall()
            stats['indexes'] = [{'name': idx[0], 'table': idx[1]} for idx in indexes]
            
            # Cache statistics
            cache_stats = conn.execute("PRAGMA cache_size").fetchone()[0]
            stats['cache_size'] = cache_stats
            
            return stats
    
    def monitor_slow_queries(self, threshold_ms: float = 1000.0):
        """Monitor and log slow queries."""
        # This would be implemented with query logging in a production system
        logger.info(f"Monitoring queries slower than {threshold_ms}ms")
        
        # In a real implementation, this would:
        # 1. Hook into SQLite's query execution
        # 2. Log queries exceeding the threshold
        # 3. Provide recommendations for optimization
        pass


class CacheManager:
    """In-memory caching for frequently accessed data."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._access_times = {}
        self._creation_times = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        if key not in self._cache:
            return None
        
        # Check TTL
        if time.time() - self._creation_times[key] > self.ttl_seconds:
            self.delete(key)
            return None
        
        # Update access time
        self._access_times[key] = time.time()
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set item in cache."""
        # Evict if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_lru()
        
        self._cache[key] = value
        self._access_times[key] = time.time()
        self._creation_times[key] = time.time()
    
    def delete(self, key: str) -> None:
        """Delete item from cache."""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
        self._creation_times.pop(key, None)
    
    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self._access_times:
            return
        
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        self.delete(lru_key)
    
    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        self._access_times.clear()
        self._creation_times.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1),
            'ttl_seconds': self.ttl_seconds
        }


class QueryOptimizer:
    """Query optimization utilities."""
    
    @staticmethod
    def optimize_conversation_queries():
        """Optimized queries for conversation management."""
        return {
            'get_recent_conversations': """
                SELECT c.conversation_id, c.user_id, c.created_at, c.updated_at,
                       COUNT(m.message_id) as message_count,
                       MAX(m.timestamp) as last_message_time
                FROM conversations c
                LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                WHERE c.user_id = ?
                GROUP BY c.conversation_id
                ORDER BY c.updated_at DESC
                LIMIT ?
            """,
            
            'get_conversation_context': """
                SELECT m.role, m.content, m.timestamp, m.sources, m.confidence
                FROM messages m
                WHERE m.conversation_id = ?
                ORDER BY m.timestamp DESC
                LIMIT ?
            """,
            
            'get_conversation_summary': """
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN role = 'user' THEN 1 END) as user_messages,
                    COUNT(CASE WHEN role = 'assistant' THEN 1 END) as assistant_messages,
                    MIN(timestamp) as first_message,
                    MAX(timestamp) as last_message
                FROM messages
                WHERE conversation_id = ?
            """
        }
    
    @staticmethod
    def optimize_document_queries():
        """Optimized queries for document retrieval."""
        return {
            'search_documents_by_metadata': """
                SELECT DISTINCT dm.document_id, dm.title, dm.course_module, 
                       dm.document_type, dm.creation_date
                FROM document_metadata dm
                JOIN document_chunks dc ON dm.document_id = dc.document_id
                WHERE (? IS NULL OR dm.course_module = ?)
                  AND (? IS NULL OR dm.document_type = ?)
                  AND (? IS NULL OR dc.content_type = ?)
                ORDER BY dm.creation_date DESC
                LIMIT ?
            """,
            
            'get_document_chunks': """
                SELECT dc.chunk_id, dc.content, dc.content_type, 
                       dc.hierarchical_context, dc.page_number, dc.position_in_document
                FROM document_chunks dc
                WHERE dc.document_id = ?
                ORDER BY dc.position_in_document
            """,
            
            'search_chunks_by_content': """
                SELECT dc.chunk_id, dc.document_id, dc.content, dc.page_number,
                       dm.title, dm.course_module
                FROM document_chunks dc
                JOIN document_metadata dm ON dc.document_id = dm.document_id
                WHERE dc.content LIKE ?
                ORDER BY dc.document_id, dc.position_in_document
                LIMIT ?
            """
        }
    
    @staticmethod
    def optimize_analytics_queries():
        """Optimized queries for analytics and monitoring."""
        return {
            'get_query_statistics': """
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as query_count,
                    AVG(response_time) as avg_response_time,
                    AVG(confidence_score) as avg_confidence
                FROM query_logs
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """,
            
            'get_performance_metrics': """
                SELECT 
                    metric_name,
                    AVG(metric_value) as avg_value,
                    MIN(metric_value) as min_value,
                    MAX(metric_value) as max_value
                FROM performance_metrics
                WHERE timestamp >= datetime('now', '-1 hour')
                GROUP BY metric_name
            """,
            
            'get_user_activity': """
                SELECT 
                    user_id,
                    COUNT(*) as query_count,
                    AVG(response_time) as avg_response_time,
                    MAX(timestamp) as last_activity
                FROM query_logs
                WHERE timestamp >= datetime('now', '-7 days')
                GROUP BY user_id
                ORDER BY query_count DESC
                LIMIT ?
            """
        }