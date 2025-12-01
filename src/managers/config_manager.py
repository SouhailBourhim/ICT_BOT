"""
Configuration manager implementation.
"""
import json
import os
from typing import Any, Dict, Optional
from pathlib import Path
from .interfaces import ConfigurationManagerInterface
from config.logging_config import LoggerMixin


class ConfigurationManager(ConfigurationManagerInterface, LoggerMixin):
    """Configuration manager with environment variable and file support."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager."""
        self._config: Dict[str, Any] = {}
        self._config_file = config_file
        
        if config_file and Path(config_file).exists():
            self.load_config_from_file(config_file)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value with environment variable fallback."""
        # First check environment variables
        env_value = os.getenv(key.upper())
        if env_value is not None:
            return self._convert_env_value(env_value)
        
        # Then check loaded config
        if key in self._config:
            return self._config[key]
        
        # Return default
        return default
    
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config[key] = value
        self.log_debug(f"Configuration set: {key} = {value}")
    
    def load_config_from_file(self, file_path: str) -> None:
        """Load configuration from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                self._config.update(file_config)
                self.log_info(f"Configuration loaded from {file_path}")
        except Exception as e:
            self.log_error(f"Failed to load config from {file_path}: {e}")
            raise
    
    def save_config_to_file(self, file_path: Optional[str] = None) -> None:
        """Save current configuration to file."""
        target_file = file_path or self._config_file
        if not target_file:
            raise ValueError("No config file specified")
        
        try:
            Path(target_file).parent.mkdir(parents=True, exist_ok=True)
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
                self.log_info(f"Configuration saved to {target_file}")
        except Exception as e:
            self.log_error(f"Failed to save config to {target_file}: {e}")
            raise
    
    def validate_config(self) -> bool:
        """Validate configuration values."""
        required_keys = [
            "OLLAMA_MODEL",
            "CHROMA_PATH",
            "DEFAULT_K",
        ]
        
        missing_keys = []
        for key in required_keys:
            if self.get_config(key) is None:
                missing_keys.append(key)
        
        if missing_keys:
            self.log_error(f"Missing required configuration keys: {missing_keys}")
            return False
        
        # Validate specific values
        try:
            default_k = self.get_config("DEFAULT_K", 5)
            if not isinstance(default_k, int) or default_k <= 0:
                raise ValueError("DEFAULT_K must be a positive integer")
            
            max_k = self.get_config("MAX_K", 20)
            if not isinstance(max_k, int) or max_k <= 0:
                raise ValueError("MAX_K must be a positive integer")
            
            if default_k > max_k:
                raise ValueError("DEFAULT_K must be less than or equal to MAX_K")
            
            similarity_threshold = self.get_config("SIMILARITY_THRESHOLD", 0.7)
            if not isinstance(similarity_threshold, (int, float)) or not 0.0 <= similarity_threshold <= 1.0:
                raise ValueError("SIMILARITY_THRESHOLD must be between 0.0 and 1.0")
            
            self.log_info("Configuration validation passed")
            return True
            
        except ValueError as e:
            self.log_error(f"Configuration validation failed: {e}")
            return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self._config.copy()
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values."""
        self._config.update(updates)
        self.log_info(f"Configuration updated with {len(updates)} values")
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Handle boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Handle numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Handle JSON values
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # Return as string
        return value