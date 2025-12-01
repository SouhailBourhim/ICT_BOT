"""
Common utility functions and helpers.
"""
import hashlib
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path


def generate_id(prefix: str = "", length: int = 8) -> str:
    """Generate a unique ID with optional prefix."""
    timestamp = str(int(time.time() * 1000000))
    hash_obj = hashlib.md5(timestamp.encode())
    unique_id = hash_obj.hexdigest()[:length]
    return f"{prefix}{unique_id}" if prefix else unique_id


def safe_filename(filename: str) -> str:
    """Convert string to safe filename."""
    import re
    # Remove or replace unsafe characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple underscores
    safe_name = re.sub(r'_+', '_', safe_name)
    # Remove leading/trailing underscores and dots
    safe_name = safe_name.strip('_.')
    return safe_name or "unnamed"


def ensure_directory(path: str) -> Path:
    """Ensure directory exists and return Path object."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    return Path(file_path).stat().st_size


def get_file_extension(file_path: str) -> str:
    """Get file extension without dot."""
    return Path(file_path).suffix.lstrip('.').lower()


def is_supported_file(file_path: str, supported_extensions: List[str]) -> bool:
    """Check if file has supported extension."""
    extension = get_file_extension(file_path)
    return extension in [ext.lower() for ext in supported_extensions]


def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Add timing info to result if it's a dict
        if isinstance(result, dict):
            result['_execution_time'] = execution_time
        
        return result
    return wrapper


def retry_decorator(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        raise e
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def sanitize_text(text: str) -> str:
    """Sanitize text for safe processing."""
    import re
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text."""
    import re
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, text)
    return [float(match) for match in matches if match]


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity using character overlap."""
    if not text1 or not text2:
        return 0.0
    
    # Convert to sets of characters
    set1 = set(text1.lower())
    set2 = set(text2.lower())
    
    # Calculate Jaccard similarity
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0


def format_timestamp(timestamp: Optional[datetime] = None) -> str:
    """Format timestamp for display."""
    if timestamp is None:
        timestamp = datetime.utcnow()
    return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse timestamp string to datetime object."""
    formats = [
        "%Y-%m-%d %H:%M:%S UTC",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse timestamp: {timestamp_str}")


def memory_usage_mb() -> float:
    """Get current memory usage in MB."""
    import psutil
    import os
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def disk_usage_mb(path: str) -> Dict[str, float]:
    """Get disk usage information for path."""
    import shutil
    total, used, free = shutil.disk_usage(path)
    return {
        "total_mb": total / 1024 / 1024,
        "used_mb": used / 1024 / 1024,
        "free_mb": free / 1024 / 1024,
        "usage_percent": (used / total) * 100
    }