#!/bin/bash

# Build script for RAG System Docker container
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="rag-system"
TAG=${1:-latest}
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

echo -e "${BLUE}🐳 Building RAG System Docker Image${NC}"
echo "=================================="
echo "Image: ${FULL_IMAGE_NAME}"
echo "Context: $(pwd)"

# Function to clean Docker cache
clean_docker_cache() {
    echo -e "\n${YELLOW}Cleaning Docker cache...${NC}"
    docker system prune -f
    docker builder prune -f
}

# Function to check Docker space
check_docker_space() {
    echo -e "\n${YELLOW}Checking Docker disk usage...${NC}"
    docker system df
}

# Function to try different build strategies
try_build() {
    local dockerfile=$1
    local strategy=$2
    
    echo -e "\n${YELLOW}Trying build strategy: ${strategy}${NC}"
    echo "Using Dockerfile: ${dockerfile}"
    
    # Try building with different options
    if docker build \
        --no-cache \
        --progress=plain \
        -f "${dockerfile}" \
        -t "${FULL_IMAGE_NAME}" \
        . ; then
        return 0
    else
        return 1
    fi
}

# Check Docker daemon
echo -e "\n${YELLOW}Checking Docker daemon...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker daemon is not running!${NC}"
    echo "Please start Docker and try again."
    exit 1
fi

# Check available space
check_docker_space

# Try building with the main Dockerfile first
echo -e "\n${YELLOW}Step 1: Attempting build with multi-stage Dockerfile...${NC}"
if try_build "deployment/docker/Dockerfile" "Multi-stage build"; then
    BUILD_SUCCESS=1
else
    echo -e "\n${YELLOW}Multi-stage build failed. Trying simple build...${NC}"
    
    # Clean cache and try simple Dockerfile
    clean_docker_cache
    
    if try_build "Dockerfile.simple" "Simple single-stage build"; then
        BUILD_SUCCESS=1
    else
        echo -e "\n${YELLOW}Simple build failed. Trying with cache cleanup...${NC}"
        
        # More aggressive cleanup
        echo -e "${YELLOW}Performing aggressive Docker cleanup...${NC}"
        docker system prune -a -f --volumes || true
        
        # Try one more time with simple Dockerfile
        if try_build "Dockerfile.simple" "Final attempt with cleanup"; then
            BUILD_SUCCESS=1
        else
            BUILD_SUCCESS=0
        fi
    fi
fi

# Check results
if [ "$BUILD_SUCCESS" = "1" ]; then
    echo -e "\n${GREEN}✅ Docker image built successfully!${NC}"
    echo "Image: ${FULL_IMAGE_NAME}"
    
    # Show image size
    echo -e "\n${YELLOW}Image details:${NC}"
    docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
    # Test the image
    echo -e "\n${YELLOW}Testing the image...${NC}"
    if docker run --rm "${FULL_IMAGE_NAME}" python -c "import streamlit; print('✅ Streamlit import successful')"; then
        echo -e "${GREEN}✅ Image test passed!${NC}"
    else
        echo -e "${YELLOW}⚠️  Image test failed, but build completed${NC}"
    fi
    
    echo -e "\n${BLUE}🚀 Usage Instructions:${NC}"
    echo "Run container:     docker run -p 8501:8501 ${FULL_IMAGE_NAME}"
    echo "Run with compose:  cd deployment/docker && docker-compose up -d"
    echo "Health check:      ./health-check.sh"
    
else
    echo -e "\n${RED}❌ All build attempts failed!${NC}"
    echo -e "\n${YELLOW}Troubleshooting suggestions:${NC}"
    echo "1. Check Docker disk space: docker system df"
    echo "2. Clean Docker cache: docker system prune -a -f"
    echo "3. Restart Docker daemon"
    echo "4. Check Docker logs for errors"
    echo "5. Try building on a different machine"
    echo "6. Use the simple Dockerfile: docker build -f Dockerfile.simple -t ${FULL_IMAGE_NAME} ."
    
    # Show current Docker status
    echo -e "\n${YELLOW}Current Docker status:${NC}"
    docker system df
    
    exit 1
fi