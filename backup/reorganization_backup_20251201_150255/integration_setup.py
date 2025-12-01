#!/usr/bin/env python3
"""
Integration setup script for the enhanced RAG system.
This script handles the final integration and configuration of all enhanced components.
"""
import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config.settings import get_settings
from config.enhanced_config import get_enhanced_config, create_default_profiles
from utils.backward_compatibility import get_compatibility_manager
from migration_scripts.migrate_to_enhanced import DataMigrator


class IntegrationManager:
    """Manages the integration of enhanced RAG system components."""
    
    def __init__(self):
        """Initialize integration manager."""
        self.logger = self._setup_logging()
        self.config = get_settings()
        self.enhanced_config = get_enhanced_config()
        self.compatibility_manager = get_compatibility_manager()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for integration."""
        logger = logging.getLogger("integration")
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def run_integration(self, force_migration: bool = False) -> bool:
        """Run the complete integration process."""
        try:
            self.logger.info("Starting enhanced RAG system integration...")
            
            # Step 1: Validate system requirements
            if not self._validate_requirements():
                return False
            
            # Step 2: Setup configuration
            self._setup_configuration()
            
            # Step 3: Handle data migration
            if force_migration or self._needs_migration():
                if not self._run_migration():
                    return False
            
            # Step 4: Initialize enhanced components
            self._initialize_components()
            
            # Step 5: Setup backward compatibility
            self._setup_backward_compatibility()
            
            # Step 6: Validate integration
            if not self._validate_integration():
                return False
            
            # Step 7: Create deployment artifacts
            self._create_deployment_artifacts()
            
            self.logger.info("Integration completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Integration failed: {e}")
            return False
    
    def _validate_requirements(self) -> bool:
        """Validate system requirements."""
        self.logger.info("Validating system requirements...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            self.logger.error("Python 3.8 or higher is required")
            return False
        
        # Check required directories
        required_dirs = [
            "data", "logs", "config", "managers", "retrievers", 
            "processors", "ui", "utils", "core"
        ]
        
        for dir_name in required_dirs:
            if not Path(dir_name).exists():
                self.logger.error(f"Required directory missing: {dir_name}")
                return False
        
        # Check critical files
        critical_files = [
            "app.py", "config/settings.py", "core/system.py",
            "managers/interfaces.py", "requirements.txt"
        ]
        
        for file_path in critical_files:
            if not Path(file_path).exists():
                self.logger.error(f"Critical file missing: {file_path}")
                return False
        
        self.logger.info("System requirements validated successfully")
        return True
    
    def _setup_configuration(self):
        """Setup enhanced configuration."""
        self.logger.info("Setting up enhanced configuration...")
        
        # Create configuration directories
        config_dirs = ["config/profiles", "config/environments"]
        for dir_path in config_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # Create default feature profiles
        create_default_profiles()
        
        # Save enhanced configuration
        self.enhanced_config.save_to_file()
        
        # Create environment-specific configurations
        self._create_environment_configs()
        
        self.logger.info("Configuration setup completed")
    
    def _create_environment_configs(self):
        """Create environment-specific configuration files."""
        environments = {
            "development": {
                "LOG_LEVEL": "DEBUG",
                "ENABLE_PERFORMANCE_MONITORING": "false",
                "ENABLE_QUERY_ANALYTICS": "false",
                "MAX_CONCURRENT_REQUESTS": "5",
                "ENABLE_CACHING": "false"
            },
            "staging": {
                "LOG_LEVEL": "INFO",
                "ENABLE_PERFORMANCE_MONITORING": "true",
                "ENABLE_QUERY_ANALYTICS": "true",
                "MAX_CONCURRENT_REQUESTS": "10",
                "ENABLE_CACHING": "true"
            },
            "production": {
                "LOG_LEVEL": "WARNING",
                "ENABLE_PERFORMANCE_MONITORING": "true",
                "ENABLE_QUERY_ANALYTICS": "true",
                "MAX_CONCURRENT_REQUESTS": "20",
                "ENABLE_CACHING": "true",
                "CACHE_TTL_SECONDS": "7200"
            }
        }
        
        for env_name, env_config in environments.items():
            env_file = Path(f"config/environments/{env_name}.env")
            with open(env_file, 'w') as f:
                for key, value in env_config.items():
                    f.write(f"{key}={value}\n")
    
    def _needs_migration(self) -> bool:
        """Check if data migration is needed."""
        migration_status_file = Path("config/migration_status.json")
        return not migration_status_file.exists()
    
    def _run_migration(self) -> bool:
        """Run data migration."""
        self.logger.info("Running data migration...")
        
        try:
            migrator = DataMigrator()
            success = migrator.run_migration()
            
            if success:
                self.logger.info("Data migration completed successfully")
            else:
                self.logger.error("Data migration failed")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Migration error: {e}")
            return False
    
    def _initialize_components(self):
        """Initialize enhanced system components."""
        self.logger.info("Initializing enhanced components...")
        
        try:
            # Initialize core system
            from core.system import RAGSystem
            rag_system = RAGSystem()
            rag_system.initialize()
            
            # Test component initialization
            component_tests = [
                ("ConversationManager", "managers.conversation_manager", "ConversationManager"),
                ("ResponseManager", "managers.response_manager", "ResponseManager"),
                ("QueryEnhancer", "managers.query_enhancer", "QueryEnhancer"),
                ("HybridRetriever", "retrievers.hybrid_retriever", "HybridRetriever"),
                ("AnalyticsManager", "managers.analytics_manager", "AnalyticsManager"),
            ]
            
            for component_name, module_path, class_name in component_tests:
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    component_class = getattr(module, class_name)
                    component_instance = component_class()
                    self.logger.info(f"✓ {component_name} initialized successfully")
                except Exception as e:
                    self.logger.warning(f"⚠ {component_name} initialization failed: {e}")
            
            self.logger.info("Component initialization completed")
            
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            raise
    
    def _setup_backward_compatibility(self):
        """Setup backward compatibility features."""
        self.logger.info("Setting up backward compatibility...")
        
        # Check compatibility status
        compatibility_status = self.compatibility_manager.check_compatibility()
        
        # Log compatibility warnings
        for warning in compatibility_status.get("compatibility_warnings", []):
            self.logger.warning(f"Compatibility: {warning}")
        
        # Create compatibility configuration
        compatibility_config = {
            "legacy_mode_available": True,
            "enhanced_features_available": compatibility_status["enhanced_features_available"],
            "migration_completed": not compatibility_status["migration_needed"],
            "compatibility_warnings": compatibility_status["compatibility_warnings"]
        }
        
        with open("config/compatibility_status.json", 'w') as f:
            json.dump(compatibility_config, f, indent=2)
        
        self.logger.info("Backward compatibility setup completed")
    
    def _validate_integration(self) -> bool:
        """Validate the integration."""
        self.logger.info("Validating integration...")
        
        validation_checks = []
        
        # Check configuration validation
        try:
            self.config.validate()
            self.enhanced_config.enhanced_config.validate()
            validation_checks.append(("Configuration", True, ""))
        except Exception as e:
            validation_checks.append(("Configuration", False, str(e)))
        
        # Check database connectivity
        try:
            import sqlite3
            for db_path in [
                self.config.database.metadata_db_path,
                self.config.database.conversation_db_path,
                self.config.database.analytics_db_path
            ]:
                if Path(db_path).exists():
                    conn = sqlite3.connect(db_path)
                    conn.close()
            validation_checks.append(("Database Connectivity", True, ""))
        except Exception as e:
            validation_checks.append(("Database Connectivity", False, str(e)))
        
        # Check vector database
        try:
            chroma_path = Path(self.config.database.chroma_path)
            if chroma_path.exists():
                validation_checks.append(("Vector Database", True, ""))
            else:
                validation_checks.append(("Vector Database", False, "Chroma database not found"))
        except Exception as e:
            validation_checks.append(("Vector Database", False, str(e)))
        
        # Check UI components
        try:
            from ui.components import UIComponentManager
            from ui.filters import SearchEnhancementManager
            ui_manager = UIComponentManager()
            search_manager = SearchEnhancementManager()
            validation_checks.append(("UI Components", True, ""))
        except Exception as e:
            validation_checks.append(("UI Components", False, str(e)))
        
        # Report validation results
        all_passed = True
        for check_name, passed, error in validation_checks:
            if passed:
                self.logger.info(f"✓ {check_name}: PASSED")
            else:
                self.logger.error(f"✗ {check_name}: FAILED - {error}")
                all_passed = False
        
        return all_passed
    
    def _create_deployment_artifacts(self):
        """Create deployment artifacts."""
        self.logger.info("Creating deployment artifacts...")
        
        # Create startup script
        startup_script = """#!/bin/bash
# Enhanced RAG System Startup Script

echo "Starting Enhanced RAG System..."

# Check environment
if [ -f "config/environments/${ENVIRONMENT:-development}.env" ]; then
    echo "Loading environment: ${ENVIRONMENT:-development}"
    source "config/environments/${ENVIRONMENT:-development}.env"
fi

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run health check
python -c "
from core.system import RAGSystem
system = RAGSystem()
health = system.health_check()
if health['overall_status'] != 'healthy':
    print('System health check failed!')
    exit(1)
print('System health check passed')
"

# Start the application
echo "Starting Streamlit application..."
streamlit run app.py --server.port ${PORT:-8501} --server.address ${HOST:-0.0.0.0}
"""
        
        with open("start_enhanced_system.sh", 'w') as f:
            f.write(startup_script)
        
        os.chmod("start_enhanced_system.sh", 0o755)
        
        # Create system status script
        status_script = """#!/usr/bin/env python3
import json
from core.system import RAGSystem
from config.enhanced_config import get_enhanced_config
from utils.backward_compatibility import get_compatibility_manager

def main():
    print("Enhanced RAG System Status")
    print("=" * 40)
    
    # System health
    try:
        system = RAGSystem()
        health = system.health_check()
        print(f"System Status: {health['overall_status']}")
        print(f"Initialized: {health['system_initialized']}")
        print(f"Config Valid: {health['config_valid']}")
    except Exception as e:
        print(f"System Status: ERROR - {e}")
    
    # Enhanced features
    try:
        enhanced_config = get_enhanced_config()
        features = enhanced_config.get_all_features()
        enabled_features = [k for k, v in features.items() if k.startswith('enable_') and v]
        print(f"Enhanced Features: {len(enabled_features)} enabled")
    except Exception as e:
        print(f"Enhanced Features: ERROR - {e}")
    
    # Compatibility
    try:
        compat_manager = get_compatibility_manager()
        compat_status = compat_manager.check_compatibility()
        print(f"Legacy Compatibility: {'Available' if compat_status['legacy_config_available'] else 'Unavailable'}")
        print(f"Migration Status: {'Completed' if not compat_status['migration_needed'] else 'Needed'}")
    except Exception as e:
        print(f"Compatibility: ERROR - {e}")

if __name__ == "__main__":
    main()
"""
        
        with open("system_status.py", 'w') as f:
            f.write(status_script)
        
        os.chmod("system_status.py", 0o755)
        
        # Create integration summary
        integration_summary = {
            "integration_date": self._get_timestamp(),
            "system_version": "2.0.0-enhanced",
            "components_integrated": [
                "Enhanced Document Processing",
                "Hybrid Retrieval System",
                "Conversation Management",
                "Query Enhancement",
                "Response Attribution",
                "Performance Monitoring",
                "Analytics System",
                "Enhanced UI Components",
                "Backward Compatibility"
            ],
            "configuration_files": [
                "config/settings.py",
                "config/enhanced_config.py",
                "config/enhanced_features.json",
                "config/migration_status.json",
                "config/compatibility_status.json"
            ],
            "deployment_artifacts": [
                "start_enhanced_system.sh",
                "system_status.py",
                "migration_scripts/migrate_to_enhanced.py",
                "docs/ENHANCED_DEPLOYMENT_GUIDE.md"
            ]
        }
        
        with open("integration_summary.json", 'w') as f:
            json.dump(integration_summary, f, indent=2)
        
        self.logger.info("Deployment artifacts created successfully")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def generate_integration_report(self) -> Dict[str, Any]:
        """Generate comprehensive integration report."""
        report = {
            "integration_status": "completed",
            "timestamp": self._get_timestamp(),
            "system_info": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": sys.platform,
                "working_directory": str(Path.cwd())
            },
            "configuration": {
                "base_config_valid": False,
                "enhanced_config_valid": False,
                "migration_completed": False
            },
            "components": {},
            "compatibility": {},
            "recommendations": []
        }
        
        # Test configuration
        try:
            self.config.validate()
            report["configuration"]["base_config_valid"] = True
        except Exception as e:
            report["recommendations"].append(f"Fix base configuration: {e}")
        
        try:
            self.enhanced_config.enhanced_config.validate()
            report["configuration"]["enhanced_config_valid"] = True
        except Exception as e:
            report["recommendations"].append(f"Fix enhanced configuration: {e}")
        
        # Check migration status
        migration_file = Path("config/migration_status.json")
        report["configuration"]["migration_completed"] = migration_file.exists()
        
        if not migration_file.exists():
            report["recommendations"].append("Run data migration: python migration_scripts/migrate_to_enhanced.py")
        
        # Test components
        components_to_test = [
            ("ConversationManager", "managers.conversation_manager"),
            ("ResponseManager", "managers.response_manager"),
            ("HybridRetriever", "retrievers.hybrid_retriever"),
            ("AnalyticsManager", "managers.analytics_manager"),
            ("UIComponentManager", "ui.components"),
        ]
        
        for component_name, module_path in components_to_test:
            try:
                __import__(module_path)
                report["components"][component_name] = "available"
            except Exception as e:
                report["components"][component_name] = f"error: {e}"
                report["recommendations"].append(f"Fix {component_name}: {e}")
        
        # Compatibility status
        try:
            compat_status = self.compatibility_manager.check_compatibility()
            report["compatibility"] = compat_status
        except Exception as e:
            report["compatibility"]["error"] = str(e)
        
        return report


def main():
    """Main integration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced RAG System Integration")
    parser.add_argument("--force-migration", action="store_true", help="Force data migration")
    parser.add_argument("--report-only", action="store_true", help="Generate report only")
    parser.add_argument("--validate-only", action="store_true", help="Validate integration only")
    
    args = parser.parse_args()
    
    manager = IntegrationManager()
    
    if args.report_only:
        report = manager.generate_integration_report()
        print(json.dumps(report, indent=2))
        return
    
    if args.validate_only:
        success = manager._validate_integration()
        sys.exit(0 if success else 1)
    
    # Run full integration
    success = manager.run_integration(force_migration=args.force_migration)
    
    if success:
        print("\n🎉 Enhanced RAG System Integration Completed Successfully!")
        print("\n📋 Integration Summary:")
        print("✅ Configuration setup completed")
        print("✅ Enhanced components initialized")
        print("✅ Backward compatibility configured")
        print("✅ Deployment artifacts created")
        
        print("\n🚀 Next Steps:")
        print("1. Test the system: python system_status.py")
        print("2. Start the application: ./start_enhanced_system.sh")
        print("3. Access the web interface: http://localhost:8501")
        print("4. Review the deployment guide: docs/ENHANCED_DEPLOYMENT_GUIDE.md")
        
        # Generate final report
        report = manager.generate_integration_report()
        with open("final_integration_report.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n📊 Integration report saved: final_integration_report.json")
        
    else:
        print("\n❌ Integration Failed!")
        print("Check the logs for details and resolve any issues before retrying.")
        sys.exit(1)


if __name__ == "__main__":
    main()