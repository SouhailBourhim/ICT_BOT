"""
Multi-level caching system for frequently accessed data.
Implements memory cache, disk cache, and distributed cache layers.
"""

import json
import pickle
import hashlib
import time
import threading
from typing import Any, Optional, Dict, List, Callable
from pathlib import Path
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class MemoryCache:
    """Thread-safe in-memory cache with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._access_order = {}
        self._creation_times = {}
        self._lock = threading.RLock()
        self._hit_count = 0
        self._miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self._lock:
            if key not in self._cache:
                self._miss_count += 1
                return None
            
            # Check TTL
            if time.time() - self._creation_times[key] > self.ttl_seconds:
                self._delete_unsafe(key)
                self._miss_count += 1
                return None
            
            # Update access order
            self._access_order[key] = time.time()
            self._hit_count += 1
            return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set item in cache."""
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru_unsafe()
            
            self._cache[key] = value
            self._access_order[key] = time.time()
            self._creation_times[key] = time.time()
    
    def delete(self, key: str) -> None:
        """Delete item from cache."""
        with self._lock:
            self._delete_unsafe(key)
    
    def _delete_unsafe(self, key: str) -> None:
        """Delete item without locking (internal use)."""
        self._cache.pop(key, None)
        self._access_order.pop(key, None)
        self._creation_times.pop(key, None)
    
    def _evict_lru_unsafe(self) -> None:
        """Evict least recently used item (internal use)."""
        if not self._access_order:
            return
        
        lru_key = min(self._access_order.keys(), key=lambda k: self._access_order[k])
        self._delete_unsafe(lru_key)
    
    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._creation_times.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hit_count + self._miss_count
            hit_rate = self._hit_count / max(total_requests, 1)
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_count': self._hit_count,
                'miss_count': self._miss_count,
                'hit_rate': hit_rate,
                'ttl_seconds': self.ttl_seconds
            }


class DiskCache:
    """Persistent disk-based cache."""
    
    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_mb = max_size_mb
        self._lock = threading.RLock()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def _get_metadata_path(self, key: str) -> Path:
        """Get metadata file path for key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.meta"
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from disk cache."""
        with self._lock:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_metadata_path(key)
            
            if not cache_path.exists() or not meta_path.exists():
                return None
            
            try:
                # Check metadata for TTL
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                
                if time.time() - metadata['created_at'] > metadata['ttl']:
                    self._delete_files(cache_path, meta_path)
                    return None
                
                # Load cached data
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
                    
            except Exception as e:
                logger.warning(f"Failed to load from disk cache: {e}")
                self._delete_files(cache_path, meta_path)
                return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set item in disk cache."""
        with self._lock:
            try:
                # Check disk space and evict if necessary
                self._ensure_space()
                
                cache_path = self._get_cache_path(key)
                meta_path = self._get_metadata_path(key)
                
                # Save data
                with open(cache_path, 'wb') as f:
                    pickle.dump(value, f)
                
                # Save metadata
                metadata = {
                    'key': key,
                    'created_at': time.time(),
                    'ttl': ttl_seconds,
                    'size_bytes': cache_path.stat().st_size
                }
                
                with open(meta_path, 'w') as f:
                    json.dump(metadata, f)
                    
            except Exception as e:
                logger.error(f"Failed to save to disk cache: {e}")
    
    def delete(self, key: str) -> None:
        """Delete item from disk cache."""
        with self._lock:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_metadata_path(key)
            self._delete_files(cache_path, meta_path)
    
    def _delete_files(self, cache_path: Path, meta_path: Path) -> None:
        """Delete cache and metadata files."""
        try:
            if cache_path.exists():
                cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete cache files: {e}")
    
    def _ensure_space(self) -> None:
        """Ensure cache doesn't exceed size limit."""
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
        max_size_bytes = self.max_size_mb * 1024 * 1024
        
        if total_size <= max_size_bytes:
            return
        
        # Get all cache files with metadata
        cache_files = []
        for cache_file in self.cache_dir.glob("*.cache"):
            meta_file = cache_file.with_suffix(".meta")
            if meta_file.exists():
                try:
                    with open(meta_file, 'r') as f:
                        metadata = json.load(f)
                    cache_files.append((cache_file, meta_file, metadata['created_at']))
                except Exception:
                    # Delete corrupted files
                    self._delete_files(cache_file, meta_file)
        
        # Sort by creation time (oldest first)
        cache_files.sort(key=lambda x: x[2])
        
        # Delete oldest files until under limit
        for cache_file, meta_file, _ in cache_files:
            self._delete_files(cache_file, meta_file)
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
            if total_size <= max_size_bytes:
                break
    
    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            for file in self.cache_dir.glob("*"):
                if file.is_file():
                    file.unlink()
    
    def stats(self) -> Dict[str, Any]:
        """Get disk cache statistics."""
        with self._lock:
            cache_files = list(self.cache_dir.glob("*.cache"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            return {
                'file_count': len(cache_files),
                'total_size_mb': total_size / (1024 * 1024),
                'max_size_mb': self.max_size_mb,
                'cache_dir': str(self.cache_dir)
            }


class MultiLevelCache:
    """Multi-level cache combining memory and disk caches."""
    
    def __init__(self, 
                 memory_size: int = 1000,
                 memory_ttl: int = 1800,  # 30 minutes
                 disk_size_mb: int = 100,
                 disk_ttl: int = 86400):  # 24 hours
        self.memory_cache = MemoryCache(memory_size, memory_ttl)
        self.disk_cache = DiskCache(max_size_mb=disk_size_mb)
        self.disk_ttl = disk_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache (memory first, then disk)."""
        # Try memory cache first
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try disk cache
        value = self.disk_cache.get(key)
        if value is not None:
            # Promote to memory cache
            self.memory_cache.set(key, value)
            return value
        
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set item in both caches."""
        self.memory_cache.set(key, value)
        self.disk_cache.set(key, value, self.disk_ttl)
    
    def delete(self, key: str) -> None:
        """Delete item from both caches."""
        self.memory_cache.delete(key)
        self.disk_cache.delete(key)
    
    def clear(self) -> None:
        """Clear both caches."""
        self.memory_cache.clear()
        self.disk_cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        return {
            'memory': self.memory_cache.stats(),
            'disk': self.disk_cache.stats()
        }


class CacheDecorator:
    """Decorator for caching function results."""
    
    def __init__(self, cache: MultiLevelCache, ttl_seconds: int = 3600):
        self.cache = cache
        self.ttl_seconds = ttl_seconds
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_data = {
                'func': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            cache_key = hashlib.md5(json.dumps(key_data, sort_keys=True, default=str).encode()).hexdigest()
            
            # Try to get from cache
            result = self.cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            self.cache.set(cache_key, result)
            
            return result
        
        return wrapper


class CacheWarmer:
    """Utility for warming up caches with frequently accessed data."""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
    
    def warm_conversation_cache(self, conversation_manager):
        """Pre-load frequently accessed conversations."""
        logger.info("Warming conversation cache...")
        
        try:
            # Get recent active conversations
            recent_conversations = conversation_manager.get_recent_conversations(limit=50)
            
            for conv in recent_conversations:
                # Cache conversation context
                context_key = f"conversation_context_{conv['conversation_id']}"
                context = conversation_manager.get_context(conv['conversation_id'], max_tokens=2000)
                self.cache.set(context_key, context)
                
                # Cache conversation summary
                summary_key = f"conversation_summary_{conv['conversation_id']}"
                summary = conversation_manager.get_conversation_summary(conv['conversation_id'])
                self.cache.set(summary_key, summary)
            
            logger.info(f"Warmed cache with {len(recent_conversations)} conversations")
            
        except Exception as e:
            logger.error(f"Failed to warm conversation cache: {e}")
    
    def warm_document_cache(self, document_processor):
        """Pre-load frequently accessed documents."""
        logger.info("Warming document cache...")
        
        try:
            # Get popular documents
            popular_docs = document_processor.get_popular_documents(limit=20)
            
            for doc in popular_docs:
                # Cache document metadata
                metadata_key = f"document_metadata_{doc['document_id']}"
                metadata = document_processor.get_document_metadata(doc['document_id'])
                self.cache.set(metadata_key, metadata)
                
                # Cache document chunks
                chunks_key = f"document_chunks_{doc['document_id']}"
                chunks = document_processor.get_document_chunks(doc['document_id'])
                self.cache.set(chunks_key, chunks)
            
            logger.info(f"Warmed cache with {len(popular_docs)} documents")
            
        except Exception as e:
            logger.error(f"Failed to warm document cache: {e}")
    
    def warm_query_cache(self, query_enhancer):
        """Pre-load common query enhancements."""
        logger.info("Warming query cache...")
        
        try:
            # Common queries to pre-process
            common_queries = [
                "What is wireless communication?",
                "Explain path loss",
                "How does modulation work?",
                "What is SNR?",
                "Describe OFDM",
                "What are diversity techniques?",
                "Explain channel capacity",
                "How does MIMO work?",
                "What is fading?",
                "Describe error correction codes"
            ]
            
            for query in common_queries:
                enhanced_key = f"enhanced_query_{hashlib.md5(query.encode()).hexdigest()}"
                enhanced = query_enhancer.enhance_query(query, None)
                self.cache.set(enhanced_key, enhanced)
            
            logger.info(f"Warmed cache with {len(common_queries)} query enhancements")
            
        except Exception as e:
            logger.error(f"Failed to warm query cache: {e}")


# Global cache instance
_global_cache = None

def get_cache() -> MultiLevelCache:
    """Get global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = MultiLevelCache()
    return _global_cache

def cached(ttl_seconds: int = 3600):
    """Decorator for caching function results."""
    cache = get_cache()
    return CacheDecorator(cache, ttl_seconds)

def clear_all_caches():
    """Clear all caches."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear()
        logger.info("Cleared all caches")