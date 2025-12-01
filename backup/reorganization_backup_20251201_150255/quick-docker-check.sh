#!/bin/bash

# Quick Docker check script
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🐳 Quick Docker Check${NC}"
echo "==================="

# Function to check Docker with timeout
check_docker_fast() {
    echo -n "Checking Docker daemon (10s timeout)... "
    
    if timeout 10 docker version --format '{{.Server.Version}}' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker is running${NC}"
        DOCKER_VERSION=$(docker version --format '{{.Server.Version}}' 2>/dev/null)
        echo "Version: $DOCKER_VERSION"
        return 0
    else
        echo -e "${RED}❌ Docker not responding${NC}"
        return 1
    fi
}

# Function to check Docker Desktop process
check_docker_process() {
    echo -n "Checking Docker Desktop process... "
    
    if pgrep -f "Docker Desktop" > /dev/null; then
        echo -e "${GREEN}✅ Docker Desktop is running${NC}"
        return 0
    else
        echo -e "${RED}❌ Docker Desktop not running${NC}"
        return 1
    fi
}

# Function to restart Docker Desktop
restart_docker_desktop() {
    echo -e "\n${YELLOW}Restarting Docker Desktop...${NC}"
    
    # Kill Docker processes
    echo "Stopping Docker processes..."
    pkill -f "Docker Desktop" || true
    pkill -f "com.docker" || true
    
    # Wait
    sleep 3
    
    # Start Docker Desktop
    echo "Starting Docker Desktop..."
    open -a "Docker Desktop"
    
    echo -e "${GREEN}Docker Desktop restart initiated${NC}"
    echo "Please wait 30-60 seconds for Docker to fully start"
}

# Function to wait for Docker to be ready
wait_for_docker() {
    echo -e "\n${YELLOW}Waiting for Docker to be ready...${NC}"
    
    for i in {1..30}; do
        echo -n "Attempt $i/30... "
        
        if timeout 5 docker info > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Docker is ready!${NC}"
            return 0
        else
            echo "not ready yet"
            sleep 2
        fi
    done
    
    echo -e "${RED}❌ Docker failed to start within 60 seconds${NC}"
    return 1
}

# Main execution
if check_docker_fast; then
    echo -e "\n${GREEN}🎉 Docker is working properly!${NC}"
    
    # Quick test
    echo -n "Testing Docker functionality... "
    if docker run --rm hello-world > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker test passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Docker test failed${NC}"
    fi
    
else
    echo -e "\n${YELLOW}Docker is not responding. Checking process...${NC}"
    
    if check_docker_process; then
        echo -e "\n${YELLOW}Docker Desktop is running but not responding.${NC}"
        echo "This usually means Docker is starting up or has issues."
        
        read -p "Do you want to restart Docker Desktop? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            restart_docker_desktop
            wait_for_docker
        fi
    else
        echo -e "\n${RED}Docker Desktop is not running.${NC}"
        echo "Please start Docker Desktop manually:"
        echo "1. Open Docker Desktop from Applications"
        echo "2. Wait for it to fully start"
        echo "3. Run this script again"
    fi
fi

echo -e "\n${YELLOW}💡 Tips:${NC}"
echo "• If Docker is slow, try: docker system prune -f"
echo "• Check Docker Desktop settings for resource allocation"
echo "• Restart your Mac if Docker continues to have issues"