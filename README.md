# Enhanced RAG Educational Assistant System

A comprehensive Retrieval-Augmented Generation (RAG) system designed for educational content processing and intelligent question answering. This system provides advanced document processing, hybrid retrieval, conversation management, and analytics capabilities.

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- 8GB RAM minimum (16GB recommended)
- 10GB free disk space
- Ollama installed and running
- SQLite 3.35 or higher

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rag-system
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp config/.env.example .env
   # Edit .env file with your configuration
   ```

4. **Initialize the system**
   ```bash
   python src/app.py
   ```

For detailed setup instructions, see [Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md).

## 📁 Project Structure

```
├── src/                     # Main application source code
│   ├── app.py              # Application entry point
│   ├── core/               # Core system components
│   ├── managers/           # Business logic managers
│   ├── processors/         # Document processing components
│   ├── retrievers/         # Information retrieval components
│   ├── models/             # Data models and interfaces
│   ├── ui/                 # User interface components
│   └── utils/              # Utility functions and helpers
├── config/                 # Configuration files and settings
├── docs/                   # Documentation
│   ├── guides/             # User and admin guides
│   ├── deployment/         # Deployment documentation
│   └── technical/          # Technical documentation
├── tests/                  # Test suite
├── scripts/                # Utility scripts
│   ├── docker/             # Docker-related scripts
│   └── utilities/          # General utility scripts
├── demos/                  # Demonstration files and examples
├── data/                   # Data files and documents
├── deployment/             # Deployment configurations
├── migration/              # Migration scripts and tools
└── reports/                # Status and verification reports
```

## 🔧 Key Features

### Document Processing
- Semantic chunking with intelligent boundary detection
- Metadata extraction and enrichment
- Multi-format document support (PDF, text, markdown)
- Batch processing capabilities

### Hybrid Retrieval System
- Semantic search using vector embeddings
- Keyword search with BM25 algorithm
- Result fusion and re-ranking
- Context-aware retrieval

### Conversation Management
- Multi-turn conversation tracking
- Follow-up question detection
- Context preservation across sessions
- Conversation analytics

### Query Enhancement
- Automatic spell correction
- Query expansion and term suggestion
- Ambiguity detection and resolution
- Synonym handling

### Response Generation
- Multi-source response synthesis
- Citation and source attribution
- Confidence scoring
- Structured output formatting

### Analytics & Monitoring
- Performance metrics tracking
- User interaction analytics
- System health monitoring
- Real-time dashboards

## 🛠️ Usage

### Basic Usage

```python
from src.core.system import RAGSystem

# Initialize the system
system = RAGSystem()

# Process a query
response = system.query("What is machine learning?")
print(response)
```

### Running Demos

```bash
# Analytics monitoring demo
python demos/analytics_monitoring.py

# Query enhancement demo
python demos/query_enhancer.py

# Response synthesis demo
python demos/response_synthesis.py

# UI enhancements demo (requires Streamlit)
streamlit run demos/ui_enhancements.py
```

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test categories
pytest tests/test_retrieval/ -v
pytest tests/test_processing/ -v
```

## 📚 Documentation

- **[User Guide](docs/guides/USER_GUIDE.md)** - End-user documentation
- **[Admin Guide](docs/guides/ADMIN_GUIDE.md)** - System administration
- **[Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md)** - Installation and deployment
- **[Docker Guide](docs/deployment/DOCKER_DEPLOYMENT.md)** - Docker deployment
- **[Technical Documentation](docs/technical/)** - Technical specifications

## 🐳 Docker Deployment

Quick Docker deployment:

```bash
# Build and run with Docker Compose
cd deployment/docker
docker-compose up -d

# Or use the build script
chmod +x scripts/docker/build-docker.sh
./scripts/docker/build-docker.sh
```

## 🔧 Configuration

The system uses environment variables for configuration. Key settings include:

- **Database paths**: Vector DB, metadata, conversations
- **Model settings**: Ollama model parameters
- **Retrieval parameters**: Search thresholds and weights
- **Processing settings**: Chunking and batch sizes
- **Logging configuration**: Levels and output formats

See [Configuration Guide](docs/guides/ADMIN_GUIDE.md#configuration) for details.

## 🧪 Development

### Setting up Development Environment

```bash
# Install development dependencies
pip install pytest pytest-cov flake8 mypy black isort

# Run code formatting
black src/ tests/
isort src/ tests/

# Run type checking
mypy src/

# Run linting
flake8 src/ tests/
```

### Project Organization

This project follows a modular architecture with clear separation of concerns:

- **Processors**: Handle document ingestion and processing
- **Retrievers**: Implement search and retrieval algorithms
- **Managers**: Orchestrate business logic and workflows
- **Models**: Define data structures and interfaces
- **Utils**: Provide common utilities and helpers

## 📊 Monitoring

The system includes comprehensive monitoring capabilities:

- Performance metrics and timing
- Error tracking and logging
- User interaction analytics
- System resource monitoring
- Health checks and status reporting

Access monitoring dashboards at `/analytics` when running the application.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Issues**: Report bugs and request features via GitHub Issues
- **Documentation**: Check the [docs/](docs/) directory for detailed guides
- **Community**: Join our discussions for help and collaboration

## 🔄 Recent Changes

This project has undergone a major reorganization to improve maintainability and structure. See [Reorganization Report](reports/reorganization_validation_report.md) for details on the changes made.

For migration from the old structure, see [Migration Guide](migration/README.md).