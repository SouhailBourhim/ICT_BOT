#!/bin/bash

# RAG System Setup Script
# This script sets up the environment and dependencies for the RAG system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root"
        exit 1
    fi
}

# Check system requirements
check_system() {
    log "Checking system requirements..."
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.8"
    
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        error "Python 3.8 or higher is required. Found: $PYTHON_VERSION"
        exit 1
    fi
    
    success "Python $PYTHON_VERSION found"
    
    # Check available memory
    if [[ "$OS" == "linux" ]]; then
        MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    elif [[ "$OS" == "macos" ]]; then
        MEMORY_BYTES=$(sysctl -n hw.memsize)
        MEMORY_GB=$((MEMORY_BYTES / 1024 / 1024 / 1024))
    fi
    
    if [[ $MEMORY_GB -lt 4 ]]; then
        warning "Less than 4GB RAM available. Performance may be affected."
    else
        success "${MEMORY_GB}GB RAM available"
    fi
    
    # Check disk space
    DISK_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $DISK_SPACE -lt 5 ]]; then
        warning "Less than 5GB disk space available. May need more space for models and data."
    else
        success "${DISK_SPACE}GB disk space available"
    fi
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."
    
    if [[ "$OS" == "linux" ]]; then
        # Detect package manager
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y \
                build-essential \
                sqlite3 \
                libsqlite3-dev \
                curl \
                git \
                wget
        elif command -v yum &> /dev/null; then
            sudo yum update -y
            sudo yum install -y \
                gcc \
                gcc-c++ \
                sqlite \
                sqlite-devel \
                curl \
                git \
                wget
        else
            error "Unsupported package manager"
            exit 1
        fi
    elif [[ "$OS" == "macos" ]]; then
        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            log "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        brew update
        brew install sqlite curl git wget
    fi
    
    success "System dependencies installed"
}

# Setup Python virtual environment
setup_venv() {
    log "Setting up Python virtual environment..."
    
    if [[ -d ".venv" ]]; then
        warning "Virtual environment already exists. Removing..."
        rm -rf .venv
    fi
    
    python3 -m venv .venv
    source .venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    success "Virtual environment created and activated"
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    if [[ ! -f "requirements.txt" ]]; then
        error "requirements.txt not found"
        exit 1
    fi
    
    # Install requirements
    pip install -r requirements.txt
    
    # Install development dependencies
    pip install \
        pytest \
        pytest-cov \
        pytest-html \
        pytest-xdist \
        pytest-timeout \
        flake8 \
        mypy \
        bandit \
        black \
        isort
    
    success "Python dependencies installed"
}

# Setup directories
setup_directories() {
    log "Setting up directories..."
    
    mkdir -p logs
    mkdir -p cache
    mkdir -p test_reports
    mkdir -p data/vocabulary
    mkdir -p deployment/ssl
    
    # Set permissions
    chmod 755 logs cache test_reports
    
    success "Directories created"
}

# Initialize database
init_database() {
    log "Initializing database..."
    
    if [[ -f "data/rag_system.db" ]]; then
        warning "Database already exists. Backing up..."
        cp data/rag_system.db data/rag_system.db.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    # Run database initialization
    python3 -c "
from core.system import RAGSystem
system = RAGSystem()
system.initialize_database()
print('Database initialized successfully')
"
    
    success "Database initialized"
}

# Setup configuration files
setup_config() {
    log "Setting up configuration files..."
    
    # Create .env file if it doesn't exist
    if [[ ! -f ".env" ]]; then
        if [[ -f "config/.env.example" ]]; then
            cp config/.env.example .env
            log "Created .env from config/.env.example"
        else
            cat > .env << EOF
# RAG System Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///data/rag_system.db
CACHE_DIR=cache
OLLAMA_BASE_URL=http://localhost:11434
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
EOF
            log "Created default .env file"
        fi
    fi
    
    success "Configuration files setup"
}

# Install and setup Ollama
setup_ollama() {
    log "Setting up Ollama..."
    
    if ! command -v ollama &> /dev/null; then
        log "Installing Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        log "Ollama already installed"
    fi
    
    # Start Ollama service
    if [[ "$OS" == "linux" ]]; then
        sudo systemctl enable ollama
        sudo systemctl start ollama
    elif [[ "$OS" == "macos" ]]; then
        # On macOS, Ollama runs as a user service
        ollama serve &
        sleep 5
    fi
    
    # Pull required models
    log "Pulling required models..."
    ollama pull llama2:7b-chat || warning "Failed to pull llama2 model"
    ollama pull nomic-embed-text || warning "Failed to pull embedding model"
    
    success "Ollama setup completed"
}

# Run tests
run_tests() {
    log "Running tests to verify installation..."
    
    # Run smoke tests
    python3 run_tests.py --type smoke
    
    if [[ $? -eq 0 ]]; then
        success "All tests passed"
    else
        warning "Some tests failed. Check the output above."
    fi
}

# Generate SSL certificates for development
generate_ssl_certs() {
    log "Generating SSL certificates for development..."
    
    SSL_DIR="deployment/ssl"
    
    if [[ ! -f "$SSL_DIR/cert.pem" ]]; then
        openssl req -x509 -newkey rsa:4096 -keyout "$SSL_DIR/key.pem" -out "$SSL_DIR/cert.pem" \
            -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        success "SSL certificates generated"
    else
        log "SSL certificates already exist"
    fi
}

# Main setup function
main() {
    log "Starting RAG System setup..."
    
    check_root
    check_system
    install_system_deps
    setup_venv
    install_python_deps
    setup_directories
    setup_config
    init_database
    setup_ollama
    generate_ssl_certs
    run_tests
    
    success "RAG System setup completed successfully!"
    
    echo ""
    echo "Next steps:"
    echo "1. Activate the virtual environment: source .venv/bin/activate"
    echo "2. Review and update the .env file with your settings"
    echo "3. Add your documents to the data/ directory"
    echo "4. Run the ingestion script: python3 ingest_enhanced.py"
    echo "5. Start the application: streamlit run app.py"
    echo ""
    echo "For production deployment, use: docker-compose -f deployment/docker/docker-compose.yml up -d"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-ollama)
            SKIP_OLLAMA=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --skip-ollama    Skip Ollama installation"
            echo "  --skip-tests     Skip running tests"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main setup
main