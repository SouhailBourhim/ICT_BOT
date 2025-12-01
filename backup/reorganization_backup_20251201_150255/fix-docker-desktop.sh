#!/bin/bash

# Docker Desktop Fix Script for macOS
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Docker Desktop Fix Script${NC}"
echo "================================"

# Function to completely stop Docker
stop_docker() {
    echo -e "${YELLOW}Stopping all Docker processes...${NC}"
    
    # Kill Docker Desktop processes
    pkill -f "Docker Desktop" 2>/dev/null || true
    pkill -f "com.docker.hyperkit" 2>/dev/null || true
    pkill -f "vpnkit" 2>/dev/null || true
    
    # Wait a bit
    sleep 5
    
    echo -e "${GREEN}✅ Docker processes stopped${NC}"
}

# Function to clear Docker data
clear_docker_data() {
    echo -e "${YELLOW}Clearing Docker data (this may take a moment)...${NC}"
    
    # Remove Docker data (be careful with this)
    rm -rf ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw 2>/dev/null || true
    
    echo -e "${GREEN}✅ Docker data cleared${NC}"
}

# Function to start Docker Desktop
start_docker() {
    echo -e "${YELLOW}Starting Docker Desktop...${NC}"
    
    # Start Docker Desktop
    open -a "Docker Desktop"
    
    echo -e "${GREEN}✅ Docker Desktop started${NC}"
    echo -e "${YELLOW}Please wait 2-3 minutes for Docker to fully initialize${NC}"
}

# Function to check system resources
check_resources() {
    echo -e "${YELLOW}Checking system resources...${NC}"
    
    # Check available memory
    memory_gb=$(sysctl hw.memsize | awk '{print int($2/1024/1024/1024)}')
    echo "Available RAM: ${memory_gb}GB"
    
    # Check disk space
    disk_space=$(df -h / | awk 'NR==2 {print $4}')
    echo "Available disk space: ${disk_space}"
    
    if [ "$memory_gb" -lt 8 ]; then
        echo -e "${RED}⚠️  Warning: Less than 8GB RAM detected${NC}"
        echo -e "${YELLOW}Consider reducing Docker memory allocation${NC}"
    fi
}

# Main execution
echo -e "${BLUE}Step 1: Checking system resources${NC}"
check_resources

echo -e "\n${BLUE}Step 2: Stopping Docker completely${NC}"
stop_docker

echo -e "\n${BLUE}Step 3: Starting Docker Desktop${NC}"
start_docker

echo -e "\n${GREEN}🎉 Docker Desktop restart complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Wait 2-3 minutes for Docker to fully start"
echo "2. Look for the Docker whale icon in your menu bar"
echo "3. When ready, test with: docker --version"
echo "4. If still having issues, try the factory reset option below"

echo -e "\n${RED}If Docker still doesn't work:${NC}"
echo "1. Open Docker Desktop manually"
echo "2. Go to Settings > Troubleshoot"
echo "3. Click 'Reset to factory defaults'"
echo "4. Wait for the reset to complete"