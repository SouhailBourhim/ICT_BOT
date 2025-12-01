# Project Structure Documentation

This document provides a comprehensive overview of the Enhanced RAG Educational Assistant System's directory structure and organization.

## Overview

The project follows a modular architecture with clear separation of concerns, organized into logical directories that group related functionality together.

## Root Directory Structure

```
rag-system/
├── src/                     # Main application source code
├── config/                  # Configuration files and settings
├── docs/                    # Documentation
├── tests/                   # Test suite
├── scripts/                 # Utility scripts and tools
├── demos/                   # Demonstration files and examples
├── data/                    # Data files and documents
├── deployment/              # Deployment configurations
├── migration/               # Migration scripts and tools
├── reports/                 # Status and verification reports
├── logs/                    # Application logs
├── chroma/                  # Vector database storage
├── backup/                  # System backups
├── .kiro/                   # Kiro IDE specifications
├── .github/                 # GitHub workflows and templates
├── requirements.txt         # Python dependencies
├── pytest.ini              # Test configuration
└── README.md               # Main project documentation
```

## Detailed Directory Breakdown

### `/src/` - Source Code

The main application source code organized into logical modules:

```
src/
├── app.py                   # Main application entry point
├── core/                    # Core system components
│   ├── __init__.py
│   └── system.py           # Main system orchestrator
├── managers/                # Business logic managers
│   ├── __init__.py
│   ├── interfaces.py       # Manager interfaces
│   ├── analytics_manager.py
│   ├── config_manager.py
│   ├── conversation_manager.py
│   ├── followup_detector.py
│   ├── performance_monitor.py
│   ├── query_enhancer.py
│   ├── response_manager.py
│   └── synthesis_manager.py
├── processors/              # Document processing components
│   ├── __init__.py
│   ├── interfaces.py       # Processor interfaces
│   ├── document_processor.py
│   ├── ingestion_pipeline.py
│   ├── metadata_extractor.py
│   └── semantic_chunker.py
├── retrievers/              # Information retrieval components
│   ├── __init__.py
│   ├── interfaces.py       # Retriever interfaces
│   ├── bm25_retriever.py
│   ├── hybrid_retriever.py
│   └── reranker.py
├── models/                  # Data models and interfaces
│   ├── __init__.py
│   └── base.py             # Base data models and enums
├── ui/                      # User interface components
│   ├── __init__.py
│   ├── components.py       # UI component definitions
│   └── filters.py          # UI filtering logic
└── utils/                   # Utility functions and helpers
    ├── __init__.py
    ├── backward_compatibility.py
    ├── caching.py
    ├── database_optimizer.py
    ├── error_handler.py
    ├── health_monitor.py
    ├── helpers.py
    └── streamlit_compat.py
```

### `/config/` - Configuration

Configuration files and settings management:

```
config/
├── __init__.py
├── .env.example            # Environment configuration template
├── settings.py             # Main system configuration
├── enhanced_config.py      # Enhanced configuration features
├── logging_config.py       # Logging configuration
├── enhanced_features.json  # Feature flags and settings
├── environments/           # Environment-specific configs
├── profiles/               # Configuration profiles
│   ├── basic_features.json
│   ├── full_features.json
│   └── performance_optimized.json
└── pytest.ini             # Test configuration
```

### `/docs/` - Documentation

Comprehensive documentation organized by category:

```
docs/
├── README.md               # Documentation overview
├── PROJECT_STRUCTURE.md    # This file
├── guides/                 # User and admin guides
│   ├── README.md
│   ├── USER_GUIDE.md      # End-user documentation
│   ├── ADMIN_GUIDE.md     # System administration
│   └── UI_ENHANCEMENTS_GUIDE.md
├── deployment/             # Deployment documentation
│   ├── README.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── DOCKER_DEPLOYMENT.md
│   ├── DOCKER_DESKTOP_GUIDE.md
│   └── ENHANCED_DEPLOYMENT_GUIDE.md
└── technical/              # Technical documentation
    ├── README.md
    ├── FRENCH_LANGUAGE_SUPPORT.md
    └── STREAMLIT_COMPATIBILITY.md
```

### `/tests/` - Test Suite

Comprehensive test coverage for all components:

```
tests/
├── __init__.py
├── test_analytics_manager.py
├── test_bm25_retriever.py
├── test_ci_automation.py
├── test_context_management.py
├── test_conversation_manager.py
├── test_end_to_end_workflows.py
├── test_error_handler.py
├── test_followup_detector.py
├── test_health_monitor.py
├── test_hybrid_retriever.py
├── test_ingestion_pipeline.py
├── test_load_testing.py
├── test_metadata_extractor.py
├── test_monitoring_integration.py
├── test_performance_benchmarks.py
├── test_performance_monitor.py
├── test_query_enhancer.py
├── test_reranker.py
├── test_response_manager.py
├── test_semantic_chunker.py
├── test_synthesis_manager.py
├── test_system_recovery.py
├── test_ui_components.py
├── test_ui_filters.py
└── test_ui_integration.py
```

### `/scripts/` - Utility Scripts

Scripts and tools organized by purpose:

```
scripts/
├── README.md
├── backup_project.py       # Project backup utility
├── file_inventory.py       # File structure analysis
├── import_analyzer.py      # Import dependency analysis
├── reorganization_prep.py  # Reorganization preparation
├── reorganize_files.py     # File reorganization script
├── test_reorganization.py  # Reorganization testing
├── validate_reorganization_script.py
├── docker/                 # Docker-related scripts
│   ├── README.md
│   ├── build-docker.sh
│   ├── docker-troubleshoot.sh
│   ├── fix-docker-desktop.sh
│   ├── quick-docker-check.sh
│   ├── setup-colima.sh
│   └── start-docker.sh
└── utilities/              # General utility scripts
    ├── README.md
    ├── health-check.sh
    └── start_enhanced_system.sh
```

### `/demos/` - Demonstration Files

Example scripts showcasing system capabilities:

```
demos/
├── README.md
├── analytics_monitoring.py  # Analytics demo
├── query_enhancer.py       # Query enhancement demo
├── response_synthesis.py   # Response synthesis demo
└── ui_enhancements.py      # UI components demo
```

### `/deployment/` - Deployment Configurations

Production deployment configurations:

```
deployment/
├── docker/                 # Docker deployment files
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── nginx.conf
│   ├── prometheus.yml/
│   └── ssl/
└── scripts/                # Deployment scripts
    ├── deploy.sh
    └── setup.sh
```

### `/migration/` - Migration Tools

Tools for system migrations and upgrades:

```
migration/
├── README.md
└── scripts/                # Migration scripts
```

### `/reports/` - Status and Reports

System status and verification reports:

```
reports/
├── README.md
├── FINAL_VERIFICATION.md
├── INTEGRATION_COMPLETE.md
├── ISSUE_RESOLUTION.md
├── final_integration_report.json
├── integration_status.json
├── migration_status.json
├── reorganization_validation_report.md
└── system_status.py
```

### `/data/` - Data Files

Document storage and vocabulary files:

```
data/
├── *.pdf                   # Educational documents
├── analytics.db            # Analytics database
├── conversations.db        # Conversation history
├── metadata.db            # Document metadata
└── vocabulary/             # Vocabulary and term files
    ├── ambiguous_terms.json
    ├── common_misspellings.json
    ├── synonyms.json
    └── technical_terms.txt
```

## Design Principles

### 1. Separation of Concerns
- Each directory has a specific purpose and responsibility
- Related functionality is grouped together
- Clear boundaries between different system layers

### 2. Modularity
- Components are loosely coupled and highly cohesive
- Interfaces define clear contracts between modules
- Easy to test, maintain, and extend individual components

### 3. Scalability
- Structure supports adding new features without major reorganization
- Clear patterns for extending functionality
- Organized for team development and collaboration

### 4. Maintainability
- Logical organization makes code easy to find and understand
- Consistent naming conventions and structure
- Clear documentation and examples

## Navigation Guidelines

### Finding Components
- **Core functionality**: Look in `/src/core/`
- **Business logic**: Check `/src/managers/`
- **Data processing**: Find in `/src/processors/`
- **Search functionality**: Located in `/src/retrievers/`
- **Configuration**: All in `/config/`
- **Documentation**: Organized in `/docs/`

### Adding New Features
1. Identify the appropriate module category
2. Follow existing patterns and interfaces
3. Add corresponding tests in `/tests/`
4. Update documentation in `/docs/`
5. Add demos if applicable in `/demos/`

### Development Workflow
1. Start with interface definitions in appropriate module
2. Implement core functionality following existing patterns
3. Add comprehensive tests
4. Update configuration if needed
5. Document new features and usage

## File Naming Conventions

- **Python modules**: `snake_case.py`
- **Configuration files**: `snake_case.py` or `kebab-case.json`
- **Documentation**: `UPPER_CASE.md` for major docs, `Title_Case.md` for guides
- **Scripts**: `snake_case.py` or `kebab-case.sh`
- **Test files**: `test_module_name.py`

## Import Patterns

The project uses consistent import patterns:

```python
# Absolute imports from src root
from src.core.system import RAGSystem
from src.managers.config_manager import ConfigurationManager

# Relative imports within modules
from .interfaces import ProcessorInterface
from ..models.base import BaseModel
```

## Configuration Management

Configuration follows a hierarchical approach:
1. Environment variables (highest priority)
2. Configuration files
3. Default values (lowest priority)

This structure provides flexibility while maintaining clear organization and easy maintenance.