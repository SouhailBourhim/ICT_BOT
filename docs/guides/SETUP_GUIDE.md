# Setup and Installation Guide

This guide provides comprehensive instructions for setting up the Enhanced RAG Educational Assistant System.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Setup](#quick-setup)
3. [Detailed Installation](#detailed-installation)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows 10/11
- **Python**: 3.8 or higher (3.9+ recommended)
- **Memory**: 8GB RAM minimum (16GB recommended)
- **Storage**: 10GB free disk space
- **Network**: Internet connection for downloading models and dependencies

### Required Software

1. **Python 3.8+**
   ```bash
   # Check Python version
   python --version
   # or
   python3 --version
   ```

2. **Git**
   ```bash
   # Check Git installation
   git --version
   ```

3. **Ollama** (for local LLM inference)
   ```bash
   # Install Ollama (Linux/macOS)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # For Windows, download from https://ollama.ai/download
   ```

4. **SQLite 3.35+**
   ```bash
   # Check SQLite version
   sqlite3 --version
   ```

## Quick Setup

### Automated Setup Script

The fastest way to get started:

```bash
# Clone the repository
git clone <repository-url>
cd rag-system

# Run automated setup
chmod +x deployment/scripts/setup.sh
./deployment/scripts/setup.sh
```

The setup script will:
- Check system requirements
- Create Python virtual environment
- Install dependencies
- Set up configuration
- Initialize databases
- Download and configure Ollama models
- Run verification tests

### Manual Quick Setup

If you prefer manual control:

```bash
# 1. Clone repository
git clone <repository-url>
cd rag-system

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up configuration
cp config/.env.example .env
# Edit .env with your settings

# 5. Initialize system
python src/app.py
```

## Detailed Installation

### Step 1: Environment Setup

1. **Create Project Directory**
   ```bash
   mkdir rag-system-workspace
   cd rag-system-workspace
   ```

2. **Clone Repository**
   ```bash
   git clone <repository-url> .
   ```

3. **Create Virtual Environment**
   ```bash
   # Using venv (recommended)
   python -m venv .venv
   
   # Or using conda
   conda create -n rag-system python=3.9
   ```

4. **Activate Virtual Environment**
   ```bash
   # venv (Linux/macOS)
   source .venv/bin/activate
   
   # venv (Windows)
   .venv\Scripts\activate
   
   # conda
   conda activate rag-system
   ```

### Step 2: Install Dependencies

1. **Core Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Development Dependencies** (optional)
   ```bash
   pip install pytest pytest-cov flake8 mypy black isort
   ```

3. **Verify Installation**
   ```bash
   pip list | grep -E "(streamlit|chromadb|ollama)"
   ```

### Step 3: Ollama Setup

1. **Install Ollama**
   ```bash
   # Linux/macOS
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Start Ollama service
   ollama serve
   ```

2. **Download Models**
   ```bash
   # Download default model (in another terminal)
   ollama pull llama3
   
   # Or download specific model
   ollama pull mistral
   ```

3. **Verify Ollama**
   ```bash
   ollama list
   curl http://localhost:11434/api/tags
   ```

### Step 4: Database Setup

1. **Create Data Directories**
   ```bash
   mkdir -p data chroma logs
   ```

2. **Initialize Databases**
   ```bash
   # The system will create databases on first run
   python -c "from src.core.system import RAGSystem; RAGSystem().health_check()"
   ```

## Configuration

### Environment Configuration

1. **Copy Template**
   ```bash
   cp config/.env.example .env
   ```

2. **Edit Configuration**
   ```bash
   # Edit with your preferred editor
   nano .env
   # or
   vim .env
   ```

### Key Configuration Options

```bash
# Model Configuration
OLLAMA_MODEL=llama3
OLLAMA_BASE_URL=http://localhost:11434
MODEL_TEMPERATURE=0.7

# Database Paths
CHROMA_DB_PATH=./chroma
METADATA_DB_PATH=./data/metadata.db
CONVERSATIONS_DB_PATH=./data/conversations.db
ANALYTICS_DB_PATH=./data/analytics.db

# Processing Settings
MAX_CHUNK_SIZE=2000
CHUNK_OVERLAP=200
BATCH_SIZE=10

# Retrieval Settings
SIMILARITY_THRESHOLD=0.7
MAX_RESULTS=10
RERANK_TOP_K=5

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/rag_system.log
```

### Advanced Configuration

1. **Feature Profiles**
   ```bash
   # Use different feature sets
   cp config/profiles/basic_features.json config/current_profile.json
   # or
   cp config/profiles/full_features.json config/current_profile.json
   ```

2. **Environment-Specific Settings**
   ```bash
   # Development
   cp config/environments/development.json config/environment.json
   
   # Production
   cp config/environments/production.json config/environment.json
   ```

## Verification

### System Health Check

```bash
# Run comprehensive health check
python -c "
from src.core.system import RAGSystem
system = RAGSystem()
health = system.health_check()
print('System Status:', health['overall_status'])
for component, status in health.items():
    print(f'{component}: {status}')
"
```

### Component Testing

```bash
# Test individual components
python -m pytest tests/test_core/ -v
python -m pytest tests/test_managers/ -v
python -m pytest tests/test_processors/ -v
```

### Application Startup

```bash
# Test application startup
python src/app.py --test-mode

# Or run with Streamlit
streamlit run src/app.py
```

### Demo Scripts

```bash
# Run demonstration scripts
python demos/query_enhancer.py
python demos/analytics_monitoring.py
python demos/response_synthesis.py

# Interactive UI demo
streamlit run demos/ui_enhancements.py
```

## Troubleshooting

### Common Issues

1. **Python Version Issues**
   ```bash
   # Check Python version
   python --version
   
   # Use specific Python version
   python3.9 -m venv .venv
   ```

2. **Dependency Conflicts**
   ```bash
   # Clear pip cache
   pip cache purge
   
   # Reinstall dependencies
   pip uninstall -r requirements.txt -y
   pip install -r requirements.txt
   ```

3. **Ollama Connection Issues**
   ```bash
   # Check Ollama status
   curl http://localhost:11434/api/tags
   
   # Restart Ollama
   pkill ollama
   ollama serve
   ```

4. **Database Permission Issues**
   ```bash
   # Fix permissions
   chmod 755 data/ chroma/ logs/
   chmod 644 data/*.db
   ```

5. **Port Conflicts**
   ```bash
   # Check port usage
   lsof -i :8501  # Streamlit default
   lsof -i :11434 # Ollama default
   
   # Use different ports
   streamlit run src/app.py --server.port 8502
   ```

### Debug Mode

```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python src/app.py

# Or set in .env file
echo "LOG_LEVEL=DEBUG" >> .env
```

### Log Analysis

```bash
# View recent logs
tail -f logs/rag_system.log

# Search for errors
grep -i error logs/rag_system.log

# View structured logs
python -c "
import json
with open('logs/rag_system.log') as f:
    for line in f:
        try:
            log = json.loads(line)
            if log.get('level') == 'ERROR':
                print(json.dumps(log, indent=2))
        except:
            print(line.strip())
"
```

### Performance Issues

1. **Memory Usage**
   ```bash
   # Monitor memory usage
   python -c "
   import psutil
   process = psutil.Process()
   print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
   "
   ```

2. **Database Optimization**
   ```bash
   # Optimize databases
   python -c "
   from src.utils.database_optimizer import optimize_databases
   optimize_databases()
   "
   ```

### Getting Help

1. **Check Documentation**
   - [User Guide](USER_GUIDE.md)
   - [Admin Guide](ADMIN_GUIDE.md)
   - [Technical Documentation](../technical/)

2. **Run Diagnostics**
   ```bash
   python scripts/utilities/health-check.sh
   ```

3. **System Information**
   ```bash
   python -c "
   import sys, platform, psutil
   print(f'Python: {sys.version}')
   print(f'Platform: {platform.platform()}')
   print(f'CPU: {psutil.cpu_count()} cores')
   print(f'Memory: {psutil.virtual_memory().total / 1024**3:.1f} GB')
   print(f'Disk: {psutil.disk_usage('.').free / 1024**3:.1f} GB free')
   "
   ```

## Next Steps

After successful installation:

1. **Load Documents**
   ```bash
   python ingest_enhanced.py --directory ./data
   ```

2. **Explore Features**
   - Run demo scripts in `/demos/`
   - Try the web interface with Streamlit
   - Explore analytics dashboard

3. **Customize Configuration**
   - Adjust model parameters
   - Configure retrieval settings
   - Set up monitoring

4. **Development**
   - Read the [Development Guide](../technical/DEVELOPMENT.md)
   - Explore the codebase structure
   - Run the test suite

For production deployment, see the [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md).