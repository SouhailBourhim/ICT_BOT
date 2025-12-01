#!/bin/bash

# Docker troubleshooting script for RAG System
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Docker Troubleshooting Tool${NC}"
echo "=============================="

# Function to check Docker daemon
check_docker_daemon() {
    echo -e "\n${YELLOW}Checking Docker daemon...${NC}"
    if docker info > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker daemon is running${NC}"
        docker version --format "Version: {{.Server.Version}}"
        return 0
    else
        echo -e "${RED}❌ Docker daemon is not running${NC}"
        return 1
    fi
}

# Function to check Docker disk usage
check_disk_usage() {
    echo -e "\n${YELLOW}Docker disk usage:${NC}"
    docker system df
    
    echo -e "\n${YELLOW}System disk usage:${NC}"
    df -h /var/lib/docker 2>/dev/null || df -h /
}

# Function to check Docker memory
check_docker_memory() {
    echo -e "\n${YELLOW}Docker memory settings:${NC}"
    
    # Check if we can get Docker info
    if docker info > /dev/null 2>&1; then
        TOTAL_MEM=$(docker info --format '{{.MemTotal}}' 2>/dev/null || echo "Unknown")
        echo "Available to Docker: $TOTAL_MEM bytes"
        
        # Check system memory
        if command -v free > /dev/null; then
            echo -e "\n${YELLOW}System memory:${NC}"
            free -h
        fi
    else
        echo "Cannot check Docker memory (daemon not running)"
    fi
}

# Function to clean Docker resources
clean_docker_resources() {
    echo -e "\n${YELLOW}Cleaning Docker resources...${NC}"
    
    echo "Removing stopped containers..."
    docker container prune -f
    
    echo "Removing unused images..."
    docker image prune -f
    
    echo "Removing unused volumes..."
    docker volume prune -f
    
    echo "Removing unused networks..."
    docker network prune -f
    
    echo "Removing build cache..."
    docker builder prune -f
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Function to aggressive cleanup
aggressive_cleanup() {
    echo -e "\n${RED}⚠️  Performing aggressive cleanup (removes ALL unused resources)${NC}"
    read -p "Are you sure? This will remove all unused images, containers, volumes, and networks (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Performing aggressive cleanup..."
        docker system prune -a -f --volumes
        echo -e "${GREEN}✅ Aggressive cleanup completed${NC}"
    else
        echo "Aggressive cleanup cancelled"
    fi
}

# Function to restart Docker (macOS/Linux)
restart_docker() {
    echo -e "\n${YELLOW}Restarting Docker...${NC}"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "Restarting Docker Desktop on macOS..."
        osascript -e 'quit app "Docker Desktop"'
        sleep 5
        open -a "Docker Desktop"
        echo "Docker Desktop restart initiated. Please wait for it to start..."
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "Restarting Docker service on Linux..."
        if command -v systemctl > /dev/null; then
            sudo systemctl restart docker
        elif command -v service > /dev/null; then
            sudo service docker restart
        else
            echo "Cannot restart Docker automatically. Please restart manually."
        fi
    else
        echo "Cannot restart Docker automatically on this OS. Please restart manually."
    fi
}

# Function to test simple build
test_simple_build() {
    echo -e "\n${YELLOW}Testing simple Docker build...${NC}"
    
    # Create a minimal test Dockerfile
    cat > Dockerfile.test << 'EOF'
FROM python:3.10-slim
RUN echo "Test build successful"
CMD ["echo", "Hello from Docker"]
EOF
    
    if docker build -f Dockerfile.test -t docker-test . > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Simple build test passed${NC}"
        docker rmi docker-test > /dev/null 2>&1
        rm Dockerfile.test
        return 0
    else
        echo -e "${RED}❌ Simple build test failed${NC}"
        rm -f Dockerfile.test
        return 1
    fi
}

# Function to check for common issues
check_common_issues() {
    echo -e "\n${YELLOW}Checking for common issues...${NC}"
    
    # Check disk space
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 90 ]; then
        echo -e "${RED}❌ Low disk space: ${DISK_USAGE}% used${NC}"
        echo "   Consider freeing up disk space"
    else
        echo -e "${GREEN}✅ Disk space OK: ${DISK_USAGE}% used${NC}"
    fi
    
    # Check if Docker is using too much space
    DOCKER_SIZE=$(docker system df --format "table {{.Size}}" | tail -n +2 | head -1 | sed 's/[^0-9.]//g')
    if [ ! -z "$DOCKER_SIZE" ] && [ "${DOCKER_SIZE%.*}" -gt 10 ]; then
        echo -e "${YELLOW}⚠️  Docker is using significant space: ${DOCKER_SIZE}${NC}"
        echo "   Consider running cleanup"
    fi
    
    # Check for permission issues (Linux)
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if ! docker ps > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  Possible permission issue${NC}"
            echo "   Try: sudo usermod -aG docker \$USER && newgrp docker"
        fi
    fi
}

# Function to show Docker configuration
show_docker_config() {
    echo -e "\n${YELLOW}Docker configuration:${NC}"
    
    if docker info > /dev/null 2>&1; then
        echo "Storage Driver: $(docker info --format '{{.Driver}}')"
        echo "Logging Driver: $(docker info --format '{{.LoggingDriver}}')"
        echo "Cgroup Driver: $(docker info --format '{{.CgroupDriver}}')"
        echo "Docker Root Dir: $(docker info --format '{{.DockerRootDir}}')"
    else
        echo "Cannot get Docker configuration (daemon not running)"
    fi
}

# Main menu
show_menu() {
    echo -e "\n${YELLOW}Troubleshooting Options:${NC}"
    echo "1) 🔍 Check Docker status and configuration"
    echo "2) 💾 Check disk usage and memory"
    echo "3) 🧹 Clean Docker resources (safe)"
    echo "4) 🗑️  Aggressive cleanup (removes all unused resources)"
    echo "5) 🔄 Restart Docker daemon"
    echo "6) 🧪 Test simple Docker build"
    echo "7) ⚠️  Check for common issues"
    echo "8) 📋 Show full Docker info"
    echo "9) 🚀 Try building RAG system with simple Dockerfile"
    echo "0) ❌ Exit"
    echo
}

# Main loop
while true; do
    show_menu
    read -p "Choose an option (0-9): " choice
    
    case $choice in
        1)
            check_docker_daemon
            show_docker_config
            ;;
        2)
            check_disk_usage
            check_docker_memory
            ;;
        3)
            clean_docker_resources
            ;;
        4)
            aggressive_cleanup
            ;;
        5)
            restart_docker
            ;;
        6)
            test_simple_build
            ;;
        7)
            check_common_issues
            ;;
        8)
            echo -e "\n${YELLOW}Full Docker info:${NC}"
            docker info 2>/dev/null || echo "Docker daemon not running"
            ;;
        9)
            echo -e "\n${YELLOW}Building RAG system with simple Dockerfile...${NC}"
            if [ -f "Dockerfile.simple" ]; then
                docker build -f Dockerfile.simple -t rag-system:latest .
            else
                echo -e "${RED}❌ Dockerfile.simple not found${NC}"
            fi
            ;;
        0)
            echo -e "\n${BLUE}👋 Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}❌ Invalid option${NC}"
            ;;
    esac
    
    echo
    read -p "Press Enter to continue..."
done