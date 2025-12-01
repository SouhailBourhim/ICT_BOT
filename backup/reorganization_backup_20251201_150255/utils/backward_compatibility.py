"""
Backward compatibility utilities for the enhanced RAG system.
"""
import warnings
from typing import Any, Dict, Optional, List
from functools import wraps
from pathlib import Path

from config.settings import get_settings
from config.enhanced_config import get_enhanced_config


class CompatibilityWarning(UserWarning):
    """Warning for deprecated functionality."""
    pass


def deprecated(reason: str = "This function is deprecated"):
    """Decorator to mark functions as deprecated."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated: {reason}",
                CompatibilityWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


class LegacyConfigAdapter:
    """Adapter to maintain compatibility with legacy configuration."""
    
    def __init__(self):
        """Initialize legacy config adapter."""
        self.config = get_settings()
        self.enhanced_config = get_enhanced_config()
    
    @deprecated("Use config.settings.get_settings() instead")
    def get_chroma_path(self) -> str:
        """Legacy method to get Chroma path."""
        return self.config.database.chroma_path
    
    @deprecated("Use config.settings.get_settings() instead")
    def get_ollama_model(self) -> str:
        """Legacy method to get Ollama model."""
        return self.config.model.ollama_model
    
    @deprecated("Use config.settings.get_settings() instead")
    def get_default_k(self) -> int:
        """Legacy method to get default k value."""
        return self.config.retrieval.default_k
    
    def get_legacy_config(self) -> Dict[str, Any]:
        """Get configuration in legacy format."""
        return {
            "CHROMA_PATH": self.config.database.chroma_path,
            "OLLAMA_MODEL": self.config.model.ollama_model,
            "DEFAULT_K": self.config.retrieval.default_k,
            "SIMILARITY_THRESHOLD": self.config.retrieval.similarity_threshold,
            "MAX_TOKENS": self.config.model.max_tokens,
            "TEMPERATURE": self.config.model.temperature
        }


class LegacyRetrieverAdapter:
    """Adapter for legacy retriever interface."""
    
    def __init__(self, enhanced_retriever=None):
        """Initialize with optional enhanced retriever."""
        self.enhanced_retriever = enhanced_retriever
        self.config = get_settings()
    
    @deprecated("Use retrievers.hybrid_retriever.HybridRetriever instead")
    def retrieve_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Legacy document retrieval method."""
        if self.enhanced_retriever:
            # Use enhanced retriever with legacy interface
            results = self.enhanced_retriever.retrieve(query, {}, k)
            return [self._convert_to_legacy_format(result) for result in results]
        else:
            # Fallback to basic retrieval
            return self._basic_retrieve(query, k)
    
    def _convert_to_legacy_format(self, result) -> Dict[str, Any]:
        """Convert enhanced result to legacy format."""
        return {
            "content": result.content,
            "metadata": {
                "source": result.document_id,
                "page": getattr(result, 'page_number', None),
                "score": getattr(result, 'relevance_score', None)
            }
        }
    
    def _basic_retrieve(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Basic retrieval fallback."""
        try:
            from langchain_chroma import Chroma
            from langchain_ollama import OllamaEmbeddings
            
            embeddings = OllamaEmbeddings(model=self.config.model.ollama_model)
            db = Chroma(persist_directory=self.config.database.chroma_path, embedding_function=embeddings)
            
            docs = db.similarity_search(query, k=k)
            return [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]
            
        except Exception as e:
            warnings.warn(f"Legacy retrieval failed: {e}", CompatibilityWarning)
            return []


class LegacyResponseAdapter:
    """Adapter for legacy response format."""
    
    def __init__(self, enhanced_response_manager=None):
        """Initialize with optional enhanced response manager."""
        self.enhanced_response_manager = enhanced_response_manager
    
    @deprecated("Use managers.response_manager.ResponseManager instead")
    def generate_response(self, query: str, context: List[Dict]) -> str:
        """Legacy response generation method."""
        if self.enhanced_response_manager:
            # Convert legacy context to enhanced format
            enhanced_context = self._convert_context_to_enhanced(context)
            result = self.enhanced_response_manager.generate_response(query, enhanced_context, None)
            return result.response
        else:
            # Fallback to basic response generation
            return self._basic_generate_response(query, context)
    
    def _convert_context_to_enhanced(self, legacy_context: List[Dict]) -> List:
        """Convert legacy context format to enhanced format."""
        # This would need to be implemented based on the enhanced format
        # For now, return as-is
        return legacy_context
    
    def _basic_generate_response(self, query: str, context: List[Dict]) -> str:
        """Basic response generation fallback."""
        try:
            from langchain_ollama import ChatOllama
            from langchain.prompts import ChatPromptTemplate
            
            config = get_settings()
            llm = ChatOllama(model=config.model.ollama_model)
            
            # Simple prompt template
            template = """
            Réponds à la question suivante en te basant sur le contexte fourni:
            
            Contexte: {context}
            
            Question: {query}
            """
            
            prompt = ChatPromptTemplate.from_template(template)
            context_text = "\n".join([doc.get("content", "") for doc in context])
            
            response = llm.invoke(prompt.format(context=context_text, query=query))
            return response.content
            
        except Exception as e:
            warnings.warn(f"Legacy response generation failed: {e}", CompatibilityWarning)
            return "Désolé, je ne peux pas répondre à cette question pour le moment."


class BackwardCompatibilityManager:
    """Main manager for backward compatibility."""
    
    def __init__(self):
        """Initialize compatibility manager."""
        self.config_adapter = LegacyConfigAdapter()
        self.retriever_adapter = LegacyRetrieverAdapter()
        self.response_adapter = LegacyResponseAdapter()
        
    def check_compatibility(self) -> Dict[str, Any]:
        """Check system compatibility status."""
        compatibility_status = {
            "legacy_config_available": True,
            "enhanced_features_available": self._check_enhanced_features(),
            "migration_needed": self._check_migration_needed(),
            "compatibility_warnings": self._get_compatibility_warnings()
        }
        
        return compatibility_status
    
    def _check_enhanced_features(self) -> bool:
        """Check if enhanced features are available."""
        try:
            enhanced_config = get_enhanced_config()
            return enhanced_config.validate_all()
        except Exception:
            return False
    
    def _check_migration_needed(self) -> bool:
        """Check if data migration is needed."""
        migration_status_file = Path("config/migration_status.json")
        return not migration_status_file.exists()
    
    def _get_compatibility_warnings(self) -> List[str]:
        """Get list of compatibility warnings."""
        warnings_list = []
        
        # Check for deprecated file structures
        old_config_file = Path("config.py")
        if old_config_file.exists():
            warnings_list.append("Old config.py file detected. Consider migrating to new configuration system.")
        
        # Check for old database structure
        if self._check_migration_needed():
            warnings_list.append("Database migration needed for enhanced features.")
        
        # Check for missing enhanced components
        enhanced_components = [
            "managers/conversation_manager.py",
            "managers/response_manager.py",
            "retrievers/hybrid_retriever.py"
        ]
        
        for component in enhanced_components:
            if not Path(component).exists():
                warnings_list.append(f"Enhanced component missing: {component}")
        
        return warnings_list
    
    def enable_legacy_mode(self) -> None:
        """Enable legacy compatibility mode."""
        enhanced_config = get_enhanced_config()
        
        # Disable enhanced features for compatibility
        enhanced_config.set_feature_config("enable_conversation_memory", False)
        enhanced_config.set_feature_config("enable_hybrid_search", False)
        enhanced_config.set_feature_config("enable_enhanced_ui", False)
        enhanced_config.set_feature_config("enable_query_analytics", False)
        
        # Save configuration
        enhanced_config.save_to_file()
        
        warnings.warn(
            "Legacy mode enabled. Enhanced features are disabled for compatibility.",
            CompatibilityWarning
        )
    
    def migrate_legacy_data(self) -> bool:
        """Migrate legacy data to enhanced format."""
        try:
            from migration_scripts.migrate_to_enhanced import DataMigrator
            
            migrator = DataMigrator()
            return migrator.run_migration()
            
        except ImportError:
            warnings.warn(
                "Migration script not available. Manual migration may be required.",
                CompatibilityWarning
            )
            return False
        except Exception as e:
            warnings.warn(f"Migration failed: {e}", CompatibilityWarning)
            return False
    
    def get_legacy_interface(self) -> Dict[str, Any]:
        """Get legacy interface adapters."""
        return {
            "config": self.config_adapter,
            "retriever": self.retriever_adapter,
            "response": self.response_adapter
        }


# Global compatibility manager
compatibility_manager = BackwardCompatibilityManager()


def get_compatibility_manager() -> BackwardCompatibilityManager:
    """Get the global compatibility manager."""
    return compatibility_manager


def ensure_backward_compatibility():
    """Ensure backward compatibility is maintained."""
    status = compatibility_manager.check_compatibility()
    
    if status["compatibility_warnings"]:
        for warning in status["compatibility_warnings"]:
            warnings.warn(warning, CompatibilityWarning)
    
    if status["migration_needed"]:
        print("⚠️  Database migration recommended for full enhanced features.")
        print("Run: python migration_scripts/migrate_to_enhanced.py")
    
    return status


# Legacy function aliases for backward compatibility
@deprecated("Use config.settings.get_settings() instead")
def get_config():
    """Legacy config getter."""
    return compatibility_manager.config_adapter.get_legacy_config()


@deprecated("Use retrievers.hybrid_retriever.HybridRetriever instead")
def get_retriever():
    """Legacy retriever getter."""
    return compatibility_manager.retriever_adapter


@deprecated("Use managers.response_manager.ResponseManager instead")
def get_response_generator():
    """Legacy response generator getter."""
    return compatibility_manager.response_adapter


if __name__ == "__main__":
    # Check compatibility when run directly
    status = ensure_backward_compatibility()
    print("Backward Compatibility Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")