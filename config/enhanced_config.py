"""
Enhanced configuration management for new features.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from config.settings import SystemConfig, get_settings


@dataclass
class EnhancedFeatureConfig:
    """Configuration for enhanced features."""
    
    # Conversation features
    enable_conversation_memory: bool = field(default_factory=lambda: os.getenv("ENABLE_CONVERSATION_MEMORY", "true").lower() == "true")
    enable_followup_detection: bool = field(default_factory=lambda: os.getenv("ENABLE_FOLLOWUP_DETECTION", "true").lower() == "true")
    conversation_summary_threshold: int = field(default_factory=lambda: int(os.getenv("CONVERSATION_SUMMARY_THRESHOLD", "20")))
    
    # Query enhancement features
    enable_query_expansion: bool = field(default_factory=lambda: os.getenv("ENABLE_QUERY_EXPANSION", "true").lower() == "true")
    enable_spell_correction: bool = field(default_factory=lambda: os.getenv("ENABLE_SPELL_CORRECTION", "true").lower() == "true")
    enable_ambiguity_detection: bool = field(default_factory=lambda: os.getenv("ENABLE_AMBIGUITY_DETECTION", "true").lower() == "true")
    query_expansion_max_terms: int = field(default_factory=lambda: int(os.getenv("QUERY_EXPANSION_MAX_TERMS", "5")))
    
    # Retrieval features
    enable_hybrid_search: bool = field(default_factory=lambda: os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true")
    enable_reranking: bool = field(default_factory=lambda: os.getenv("ENABLE_RERANKING", "true").lower() == "true")
    enable_metadata_filtering: bool = field(default_factory=lambda: os.getenv("ENABLE_METADATA_FILTERING", "true").lower() == "true")
    hybrid_search_weights: Dict[str, float] = field(default_factory=lambda: {
        "semantic": float(os.getenv("SEMANTIC_WEIGHT", "0.7")),
        "keyword": float(os.getenv("KEYWORD_WEIGHT", "0.3"))
    })
    
    # Response features
    enable_source_attribution: bool = field(default_factory=lambda: os.getenv("ENABLE_SOURCE_ATTRIBUTION", "true").lower() == "true")
    enable_confidence_scoring: bool = field(default_factory=lambda: os.getenv("ENABLE_CONFIDENCE_SCORING", "true").lower() == "true")
    enable_multi_source_synthesis: bool = field(default_factory=lambda: os.getenv("ENABLE_MULTI_SOURCE_SYNTHESIS", "true").lower() == "true")
    min_confidence_threshold: float = field(default_factory=lambda: float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.5")))
    
    # Analytics features
    enable_query_analytics: bool = field(default_factory=lambda: os.getenv("ENABLE_QUERY_ANALYTICS", "true").lower() == "true")
    enable_performance_monitoring: bool = field(default_factory=lambda: os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true")
    enable_user_feedback: bool = field(default_factory=lambda: os.getenv("ENABLE_USER_FEEDBACK", "true").lower() == "true")
    analytics_retention_days: int = field(default_factory=lambda: int(os.getenv("ANALYTICS_RETENTION_DAYS", "90")))
    
    # Processing features
    enable_semantic_chunking: bool = field(default_factory=lambda: os.getenv("ENABLE_SEMANTIC_CHUNKING", "true").lower() == "true")
    enable_enhanced_metadata: bool = field(default_factory=lambda: os.getenv("ENABLE_ENHANCED_METADATA", "true").lower() == "true")
    enable_content_type_detection: bool = field(default_factory=lambda: os.getenv("ENABLE_CONTENT_TYPE_DETECTION", "true").lower() == "true")
    
    # Error handling features
    enable_graceful_degradation: bool = field(default_factory=lambda: os.getenv("ENABLE_GRACEFUL_DEGRADATION", "true").lower() == "true")
    enable_automatic_retry: bool = field(default_factory=lambda: os.getenv("ENABLE_AUTOMATIC_RETRY", "true").lower() == "true")
    max_retry_attempts: int = field(default_factory=lambda: int(os.getenv("MAX_RETRY_ATTEMPTS", "3")))
    
    # UI features
    enable_enhanced_ui: bool = field(default_factory=lambda: os.getenv("ENABLE_ENHANCED_UI", "true").lower() == "true")
    enable_auto_complete: bool = field(default_factory=lambda: os.getenv("ENABLE_AUTO_COMPLETE", "true").lower() == "true")
    enable_advanced_filters: bool = field(default_factory=lambda: os.getenv("ENABLE_ADVANCED_FILTERS", "true").lower() == "true")
    
    def validate(self) -> bool:
        """Validate enhanced feature configuration."""
        try:
            # Validate weights sum to 1.0
            total_weight = sum(self.hybrid_search_weights.values())
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError(f"Hybrid search weights must sum to 1.0, got {total_weight}")
            
            # Validate confidence threshold
            if not 0.0 <= self.min_confidence_threshold <= 1.0:
                raise ValueError("min_confidence_threshold must be between 0.0 and 1.0")
            
            # Validate retry attempts
            if self.max_retry_attempts < 1:
                raise ValueError("max_retry_attempts must be at least 1")
            
            # Validate retention days
            if self.analytics_retention_days < 1:
                raise ValueError("analytics_retention_days must be at least 1")
            
            return True
            
        except ValueError as e:
            raise ValueError(f"Enhanced feature configuration validation failed: {e}")


class EnhancedConfigManager:
    """Manager for enhanced system configuration."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize enhanced config manager."""
        self.base_config = get_settings()
        self.enhanced_config = EnhancedFeatureConfig()
        self.config_file = config_file or "config/enhanced_features.json"
        
        # Load from file if exists
        if Path(self.config_file).exists():
            self.load_from_file()
    
    def load_from_file(self) -> None:
        """Load enhanced configuration from file."""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                
            # Update enhanced config with loaded data
            for key, value in config_data.items():
                if hasattr(self.enhanced_config, key):
                    setattr(self.enhanced_config, key, value)
                    
        except Exception as e:
            print(f"Warning: Could not load enhanced config from {self.config_file}: {e}")
    
    def save_to_file(self) -> None:
        """Save enhanced configuration to file."""
        try:
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(asdict(self.enhanced_config), f, indent=2)
                
        except Exception as e:
            print(f"Error: Could not save enhanced config to {self.config_file}: {e}")
            raise
    
    def get_feature_config(self, feature_name: str) -> Any:
        """Get configuration for a specific feature."""
        return getattr(self.enhanced_config, feature_name, None)
    
    def set_feature_config(self, feature_name: str, value: Any) -> None:
        """Set configuration for a specific feature."""
        if hasattr(self.enhanced_config, feature_name):
            setattr(self.enhanced_config, feature_name, value)
        else:
            raise ValueError(f"Unknown feature configuration: {feature_name}")
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        config_value = self.get_feature_config(feature_name)
        return bool(config_value) if config_value is not None else False
    
    def get_all_features(self) -> Dict[str, Any]:
        """Get all enhanced feature configurations."""
        return asdict(self.enhanced_config)
    
    def validate_all(self) -> bool:
        """Validate all configurations."""
        try:
            # Validate base config
            self.base_config.validate()
            
            # Validate enhanced config
            self.enhanced_config.validate()
            
            return True
            
        except ValueError as e:
            print(f"Configuration validation failed: {e}")
            return False
    
    def get_runtime_config(self) -> Dict[str, Any]:
        """Get runtime configuration combining base and enhanced configs."""
        return {
            "base": self.base_config.to_dict(),
            "enhanced": asdict(self.enhanced_config),
            "validation_status": self.validate_all()
        }
    
    def reset_to_defaults(self) -> None:
        """Reset enhanced configuration to defaults."""
        self.enhanced_config = EnhancedFeatureConfig()
    
    def create_feature_profile(self, profile_name: str, features: Dict[str, bool]) -> None:
        """Create a feature profile for easy switching."""
        profile_file = f"config/profiles/{profile_name}.json"
        Path(profile_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(profile_file, 'w') as f:
            json.dump(features, f, indent=2)
    
    def load_feature_profile(self, profile_name: str) -> None:
        """Load a feature profile."""
        profile_file = f"config/profiles/{profile_name}.json"
        
        if not Path(profile_file).exists():
            raise FileNotFoundError(f"Feature profile not found: {profile_name}")
        
        with open(profile_file, 'r') as f:
            features = json.load(f)
        
        for feature_name, enabled in features.items():
            if hasattr(self.enhanced_config, feature_name):
                setattr(self.enhanced_config, feature_name, enabled)


# Global enhanced config manager
enhanced_config_manager = EnhancedConfigManager()

# Validate on import
try:
    enhanced_config_manager.validate_all()
except Exception as e:
    print(f"Warning: Enhanced configuration validation failed: {e}")


def get_enhanced_config() -> EnhancedConfigManager:
    """Get the global enhanced configuration manager."""
    return enhanced_config_manager


def create_default_profiles():
    """Create default feature profiles."""
    manager = get_enhanced_config()
    
    # Full features profile
    manager.create_feature_profile("full_features", {
        "enable_conversation_memory": True,
        "enable_followup_detection": True,
        "enable_query_expansion": True,
        "enable_spell_correction": True,
        "enable_hybrid_search": True,
        "enable_reranking": True,
        "enable_source_attribution": True,
        "enable_confidence_scoring": True,
        "enable_query_analytics": True,
        "enable_performance_monitoring": True,
        "enable_enhanced_ui": True
    })
    
    # Basic features profile
    manager.create_feature_profile("basic_features", {
        "enable_conversation_memory": False,
        "enable_followup_detection": False,
        "enable_query_expansion": True,
        "enable_spell_correction": True,
        "enable_hybrid_search": False,
        "enable_reranking": False,
        "enable_source_attribution": True,
        "enable_confidence_scoring": False,
        "enable_query_analytics": False,
        "enable_performance_monitoring": False,
        "enable_enhanced_ui": True
    })
    
    # Performance optimized profile
    manager.create_feature_profile("performance_optimized", {
        "enable_conversation_memory": True,
        "enable_followup_detection": False,
        "enable_query_expansion": False,
        "enable_spell_correction": True,
        "enable_hybrid_search": True,
        "enable_reranking": False,
        "enable_source_attribution": True,
        "enable_confidence_scoring": False,
        "enable_query_analytics": True,
        "enable_performance_monitoring": True,
        "enable_enhanced_ui": False
    })


if __name__ == "__main__":
    # Create default profiles when run directly
    create_default_profiles()
    print("Default feature profiles created successfully!")