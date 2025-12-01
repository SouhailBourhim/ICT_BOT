#!/usr/bin/env python3
"""
Enhanced RAG System Status Checker
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_system_status():
    """Check and display system status."""
    print("🎓 Enhanced RAG System Status")
    print("=" * 50)
    
    # Check integration status
    integration_file = Path("reports/integration_status.json")
    if integration_file.exists():
        with open(integration_file) as f:
            integration_status = json.load(f)
        
        print(f"📋 Integration Status: {'✅ Completed' if integration_status.get('integration_completed') else '❌ Incomplete'}")
        print(f"🔧 System Version: {integration_status.get('system_version', 'Unknown')}")
        print(f"📅 Integration Date: {integration_status.get('integration_date', 'Unknown')}")
    else:
        print("📋 Integration Status: ❌ Not completed")
        print("💡 Run: python integration_setup.py")
        return False
    
    print("\n🔧 System Components:")
    
    # Check configuration
    try:
        from config.settings import get_settings
        config = get_settings()
        config.validate()
        print("✅ Base Configuration: Valid")
    except Exception as e:
        print(f"❌ Base Configuration: Error - {e}")
    
    try:
        from config.enhanced_config import get_enhanced_config
        enhanced_config = get_enhanced_config()
        enhanced_config.validate_all()
        print("✅ Enhanced Configuration: Valid")
    except Exception as e:
        print(f"❌ Enhanced Configuration: Error - {e}")
    
    # Check core system
    try:
        from src.core.system import RAGSystem
        system = RAGSystem()
        health = system.health_check()
        status_icon = "✅" if health.get('overall_status') == 'healthy' else "⚠️"
        print(f"{status_icon} Core System: {health.get('overall_status', 'unknown').title()}")
    except Exception as e:
        print(f"❌ Core System: Error - {e}")
    
    # Check enhanced components
    components = [
        ("Conversation Manager", "managers.conversation_manager", "ConversationManager"),
        ("Response Manager", "managers.response_manager", "ResponseManager"),
        ("Query Enhancer", "managers.query_enhancer", "QueryEnhancer"),
        ("Hybrid Retriever", "retrievers.hybrid_retriever", "HybridRetriever"),
        ("Analytics Manager", "managers.analytics_manager", "AnalyticsManager"),
        ("UI Components", "ui.components", "UIComponentManager"),
        ("Search Filters", "ui.filters", "SearchEnhancementManager"),
    ]
    
    print("\n🧩 Enhanced Components:")
    for component_name, module_path, class_name in components:
        try:
            module = __import__(module_path, fromlist=[class_name])
            component_class = getattr(module, class_name)
            # Try to instantiate
            component_instance = component_class()
            print(f"✅ {component_name}: Available")
        except Exception as e:
            print(f"⚠️  {component_name}: Error - {str(e)[:50]}...")
    
    # Check databases
    print("\n💾 Database Status:")
    try:
        config = get_settings()
        
        # Vector database
        chroma_path = Path(config.database.chroma_path)
        if chroma_path.exists():
            print("✅ Vector Database (Chroma): Available")
        else:
            print("❌ Vector Database (Chroma): Not found")
            print("💡 Run document ingestion: python ingest_enhanced.py")
        
        # Metadata database
        metadata_path = Path(config.database.metadata_db_path)
        if metadata_path.exists():
            print("✅ Metadata Database: Available")
        else:
            print("⚠️  Metadata Database: Not found (will be created)")
        
        # Conversation database
        conversation_path = Path(config.database.conversation_db_path)
        if conversation_path.exists():
            print("✅ Conversation Database: Available")
        else:
            print("⚠️  Conversation Database: Not found (will be created)")
        
        # Analytics database
        analytics_path = Path(config.database.analytics_db_path)
        if analytics_path.exists():
            print("✅ Analytics Database: Available")
        else:
            print("⚠️  Analytics Database: Not found (will be created)")
            
    except Exception as e:
        print(f"❌ Database Check: Error - {e}")
    
    # Check Ollama connectivity
    print("\n🤖 External Services:")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Ollama Service: Running ({len(models)} models available)")
        else:
            print("⚠️  Ollama Service: Running but no models found")
    except Exception:
        print("❌ Ollama Service: Not accessible")
        print("💡 Install and start Ollama: https://ollama.ai")
    
    # Feature status
    print("\n✨ Enhanced Features:")
    try:
        enhanced_config = get_enhanced_config()
        features = enhanced_config.get_all_features()
        
        feature_groups = {
            "Conversation": ["enable_conversation_memory", "enable_followup_detection"],
            "Query Processing": ["enable_query_expansion", "enable_spell_correction"],
            "Retrieval": ["enable_hybrid_search", "enable_reranking"],
            "Response": ["enable_source_attribution", "enable_confidence_scoring"],
            "Analytics": ["enable_query_analytics", "enable_performance_monitoring"],
            "UI": ["enable_enhanced_ui", "enable_auto_complete"]
        }
        
        for group_name, feature_list in feature_groups.items():
            enabled_count = sum(1 for feature in feature_list if features.get(feature, False))
            total_count = len(feature_list)
            status_icon = "✅" if enabled_count == total_count else "⚠️" if enabled_count > 0 else "❌"
            print(f"{status_icon} {group_name}: {enabled_count}/{total_count} enabled")
            
    except Exception as e:
        print(f"❌ Feature Check: Error - {e}")
    
    # Backward compatibility
    print("\n🔄 Backward Compatibility:")
    try:
        from src.utils.backward_compatibility import get_compatibility_manager
        compat_manager = get_compatibility_manager()
        compat_status = compat_manager.check_compatibility()
        
        print(f"✅ Legacy Support: {'Available' if compat_status.get('legacy_config_available') else 'Unavailable'}")
        print(f"✅ Enhanced Features: {'Available' if compat_status.get('enhanced_features_available') else 'Unavailable'}")
        
        if compat_status.get('compatibility_warnings'):
            print("⚠️  Compatibility Warnings:")
            for warning in compat_status['compatibility_warnings'][:3]:  # Show first 3
                print(f"   • {warning}")
                
    except Exception as e:
        print(f"❌ Compatibility Check: Error - {e}")
    
    # System recommendations
    print("\n💡 Recommendations:")
    
    # Check if vector database exists
    try:
        config = get_settings()
        if not Path(config.database.chroma_path).exists():
            print("📚 Run document ingestion to create vector database")
            print("   Command: python ingest_enhanced.py --input-dir data")
    except:
        pass
    
    # Check if Ollama is accessible
    try:
        import requests
        requests.get("http://localhost:11434/api/tags", timeout=2)
    except:
        print("🤖 Start Ollama service for full functionality")
        print("   Install: https://ollama.ai")
        print("   Start: ollama serve")
        print("   Pull model: ollama pull llama3")
    
    print("\n🚀 Ready to start!")
    print("   Command: ./start_enhanced_system.sh")
    print("   Access: http://localhost:8501")
    
    return True

def main():
    """Main function."""
    try:
        success = check_system_status()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Status check interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Status check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()