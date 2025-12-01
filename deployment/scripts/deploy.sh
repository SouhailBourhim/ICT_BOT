#!/bin/bash

# RAG System Deployment Script
# Handles deployment to different environments (development, staging, production)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/deployment/docker/docker-compose.yml"

# Default values
ENVIRONMENT="development"
BUILD_FRESH=false
SKIP_TESTS=false
BACKUP_DATA=true

# Logging functions
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

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy RAG System to specified environment

OPTIONS:
    -e, --environment ENV    Target environment (development|staging|production) [default: development]
    -f, --fresh             Force fresh build (no cache)
    -s, --skip-tests        Skip running tests before deployment
    -n, --no-backup         Skip data backup
    -h, --help              Show this help message

EXAMPLES:
    $0                                    # Deploy to development
    $0 -e production -f                   # Fresh production deployment
    $0 -e staging --skip-tests            # Deploy to staging without tests
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -f|--fresh)
                BUILD_FRESH=true
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            -n|--no-backup)
                BACKUP_DATA=false
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
        error "Invalid environment: $ENVIRONMENT"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Backup existing data
backup_data() {
    if [[ "$BACKUP_DATA" == "false" ]]; then
        log "Skipping data backup"
        return
    fi
    
    log "Backing up existing data..."
    
    BACKUP_DIR="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    if [[ -f "$PROJECT_ROOT/data/rag_system.db" ]]; then
        cp "$PROJECT_ROOT/data/rag_system.db" "$BACKUP_DIR/"
        log "Database backed up to $BACKUP_DIR"
    fi
    
    # Backup configuration
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        cp "$PROJECT_ROOT/.env" "$BACKUP_DIR/"
    fi
    
    # Backup logs
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        cp -r "$PROJECT_ROOT/logs" "$BACKUP_DIR/"
    fi
    
    success "Data backup completed: $BACKUP_DIR"
}

# Run tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log "Skipping tests"
        return
    fi
    
    log "Running tests before deployment..."
    
    cd "$PROJECT_ROOT"
    
    # Activate virtual environment if it exists
    if [[ -f ".venv/bin/activate" ]]; then
        source .venv/bin/activate
    fi
    
    # Run smoke tests
    python3 run_tests.py --type smoke --ci
    
    if [[ $? -ne 0 ]]; then
        error "Tests failed. Deployment aborted."
        exit 1
    fi
    
    success "All tests passed"
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    BUILD_ARGS=""
    if [[ "$BUILD_FRESH" == "true" ]]; then
        BUILD_ARGS="--no-cache --pull"
    fi
    
    # Build with environment-specific tag
    docker-compose -f "$DOCKER_COMPOSE_FILE" build $BUILD_ARGS
    
    # Tag images with environment and timestamp
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    docker tag rag-system_rag-system:latest "rag-system:$ENVIRONMENT-$TIMESTAMP"
    docker tag rag-system_rag-system:latest "rag-system:$ENVIRONMENT-latest"
    
    success "Docker images built successfully"
}

# Deploy to environment
deploy() {
    log "Deploying to $ENVIRONMENT environment..."
    
    cd "$PROJECT_ROOT"
    
    # Set environment-specific configuration
    case $ENVIRONMENT in
        development)
            export COMPOSE_PROJECT_NAME="rag-system-dev"
            export STREAMLIT_SERVER_PORT="8501"
            ;;
        staging)
            export COMPOSE_PROJECT_NAME="rag-system-staging"
            export STREAMLIT_SERVER_PORT="8502"
            ;;
        production)
            export COMPOSE_PROJECT_NAME="rag-system-prod"
            export STREAMLIT_SERVER_PORT="8503"
            ;;
    esac
    
    # Stop existing containers
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Start services
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    
    MAX_WAIT=300  # 5 minutes
    WAIT_TIME=0
    
    while [[ $WAIT_TIME -lt $MAX_WAIT ]]; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "healthy"; then
            break
        fi
        
        sleep 10
        WAIT_TIME=$((WAIT_TIME + 10))
        log "Waiting for services... ($WAIT_TIME/$MAX_WAIT seconds)"
    done
    
    if [[ $WAIT_TIME -ge $MAX_WAIT ]]; then
        error "Services failed to become healthy within $MAX_WAIT seconds"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs
        exit 1
    fi
    
    success "Deployment completed successfully"
}

# Post-deployment verification
verify_deployment() {
    log "Verifying deployment..."
    
    # Check service status
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    
    # Test application endpoint
    APP_URL="http://localhost:${STREAMLIT_SERVER_PORT}"
    
    log "Testing application at $APP_URL"
    
    for i in {1..10}; do
        if curl -f "$APP_URL/_stcore/health" &> /dev/null; then
            success "Application is responding"
            break
        fi
        
        if [[ $i -eq 10 ]]; then
            error "Application is not responding after 10 attempts"
            exit 1
        fi
        
        log "Attempt $i/10: Application not ready, waiting..."
        sleep 10
    done
    
    # Run post-deployment tests
    log "Running post-deployment verification tests..."
    
    # Test basic functionality
    RESPONSE=$(curl -s "$APP_URL" | head -n 1)
    if [[ -n "$RESPONSE" ]]; then
        success "Application is serving content"
    else
        warning "Application response is empty"
    fi
    
    success "Deployment verification completed"
}

# Show deployment summary
show_summary() {
    log "Deployment Summary"
    echo "=================="
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp: $(date)"
    echo "Application URL: http://localhost:${STREAMLIT_SERVER_PORT}"
    echo ""
    echo "Services:"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "Useful commands:"
    echo "  View logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo "  Stop services: docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "  Restart services: docker-compose -f $DOCKER_COMPOSE_FILE restart"
    echo ""
}

# Cleanup on exit
cleanup() {
    if [[ $? -ne 0 ]]; then
        error "Deployment failed. Check the logs above for details."
        
        # Show recent logs
        log "Recent logs:"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail=50
    fi
}

# Main deployment function
main() {
    trap cleanup EXIT
    
    log "Starting deployment to $ENVIRONMENT environment..."
    
    check_prerequisites
    backup_data
    run_tests
    build_images
    deploy
    verify_deployment
    show_summary
    
    success "Deployment completed successfully!"
}

# Parse arguments and run
parse_args "$@"
main