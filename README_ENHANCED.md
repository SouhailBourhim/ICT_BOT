# Enhanced RAG System Structure

This document describes the enhanced modular structure implemented for the RAG educational assistant system.

## Project Structure

```
├── processors/              # Document processing components
│   ├── __init__.py
│   └── interfaces.py       # Abstract interfaces for processors
├── retrievers/             # Retrieval system components
│   ├── __init__.py
│   └── interfaces.py       # Abstract interfaces for retrievers
├── managers/               # Management components
│   ├── __init__.py
│   ├── interfaces.py       # Abstract interfaces for managers
│   └── config_manager.py   # Configuration management implementation
├── models/                 # Data models and schemas
│   ├── __init__.py
│   └── base.py            # Base data models and enums
├── config/                 # Configuration management
│   ├── __init__.py
│   ├── settings.py        # System configuration with environment variables
│   └── logging_config.py  # Structured logging configuration
├── core/                   # Core system orchestration
│   ├── __init__.py
│   └── system.py          # Main system orchestrator
├── utils/                  # Utility functions
│   ├── __init__.py
│   └── helpers.py         # Common utility functions
├── .env.example           # Environment configuration template
├── test_structure.py      # Structure validation tests
└── README_ENHANCED.md     # This file
```

## Key Features

### 1. Modular Architecture
- **Processors**: Document processing and chunking components
- **Retrievers**: Hybrid retrieval system with semantic and keyword search
- **Managers**: Conversation, response, analytics, and configuration management
- **Models**: Structured data models with type hints
- **Core**: System orchestration and initialization

### 2. Configuration Management
- Environment variable support with `.env` files
- Structured configuration with validation
- Default values and type conversion
- Configuration file support (JSON)

### 3. Structured Logging
- JSON-structured logging for better analysis
- Configurable log levels and rotation
- Context-aware logging with metadata
- Performance and error tracking

### 4. Abstract Interfaces
- Clear contracts for all major components
- Easy testing and mocking
- Pluggable implementations
- Type safety with abstract base classes

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

Key configuration sections:
- **Database**: Paths for vector DB, metadata, conversations
- **Model**: Ollama model settings and parameters
- **Retrieval**: Search parameters and thresholds
- **Processing**: Chunking and batch processing settings
- **Logging**: Log levels, rotation, and formatting

### Validation

The system validates configuration on startup:
```python
from core.system import RAGSystem

system = RAGSystem()
health = system.health_check()
print(health['config_valid'])  # Should be True
```

## Usage

### Basic System Initialization

```python
from core.system import RAGSystem

# Initialize with default config
system = RAGSystem()

# Initialize with custom config file
system = RAGSystem("config/custom.json")

# Check system health
health = system.health_check()
print(f"System status: {health['overall_status']}")
```

### Configuration Management

```python
from managers.config_manager import ConfigurationManager

config_mgr = ConfigurationManager()

# Get configuration values
model_name = config_mgr.get_config("OLLAMA_MODEL", "llama3")
chunk_size = config_mgr.get_config("MAX_CHUNK_SIZE", 2000)

# Set configuration values
config_mgr.set_config("CUSTOM_SETTING", "value")

# Validate configuration
is_valid = config_mgr.validate_config()
```

### Logging

```python
from config.logging_config import get_logger, log_with_context

logger = get_logger("my_component")

# Standard logging
logger.info("Processing document")
logger.error("Failed to process", exc_info=True)

# Structured logging with context
log_with_context(
    logger, "info", "Document processed",
    document_id="doc123",
    processing_time=1.5,
    chunk_count=42
)
```

## Testing

Run the structure validation tests:

```bash
python test_structure.py
```

This will verify:
- All modules can be imported correctly
- System initialization works
- Configuration validation functions
- Logging system is operational
- Utility functions work as expected

## Next Steps

This enhanced structure provides the foundation for implementing:

1. **Document Processing** (Task 2): Semantic chunking and metadata extraction
2. **Hybrid Retrieval** (Task 3): BM25 + semantic search with result fusion
3. **Conversation Management** (Task 4): Context tracking and follow-up detection
4. **Query Enhancement** (Task 5): Query expansion and ambiguity detection
5. **Response Generation** (Task 6): Citation and multi-source synthesis
6. **Analytics & Monitoring** (Task 7): Performance tracking and user analytics
7. **Error Handling** (Task 8): Comprehensive error recovery
8. **UI Enhancements** (Task 9): Advanced interface features

Each component can be implemented independently while following the established interfaces and patterns.

## Dependencies

New dependencies added for enhanced functionality:
- `psutil`: System resource monitoring
- `rank-bm25`: BM25 keyword search implementation
- `python-dotenv`: Environment variable management

Install with:
```bash
pip install -r requirements.txt
```