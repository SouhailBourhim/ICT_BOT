#!/bin/bash

# Colima Setup Script - Docker Alternative for macOS
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐋 Colima Setup - Docker Alternative${NC}"
echo "===================================="

# Check if Homebrew is installed
check_homebrew() {
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}❌ Homebrew not found${NC}"
        echo -e "${YELLOW}Installing Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo -e "${GREEN}✅ Homebrew found${NC}"
    fi
}

# Install Colima and Docker CLI
install_colima() {
    echo -e "${YELLOW}Installing Colima and Docker CLI...${NC}"
    
    # Install colima and docker
    brew install colima docker
    
    echo -e "${GREEN}✅ Colima and Docker CLI installed${NC}"
}

# Start Colima
start_colima() {
    echo -e "${YELLOW}Starting Colima...${NC}"
    
    # Start colima with reasonable defaults
    colima start --cpu 2 --memory 4 --disk 60
    
    echo -e "${GREEN}✅ Colima started${NC}"
}

# Test Docker
test_docker() {
    echo -e "${YELLOW}Testing Docker...${NC}"
    
    if docker --version; then
        echo -e "${GREEN}✅ Docker CLI working${NC}"
    else
        echo -e "${RED}❌ Docker CLI not working${NC}"
        return 1
    fi
    
    if docker ps; then
        echo -e "${GREEN}✅ Docker daemon working${NC}"
    else
        echo -e "${RED}❌ Docker daemon not working${NC}"
        return 1
    fi
}

# Main execution
echo -e "${BLUE}This will install Colima as a Docker Desktop alternative${NC}"
echo -e "${YELLOW}Colima is lightweight and often more reliable than Docker Desktop${NC}"
echo

read -p "Do you want to proceed with Colima installation? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${BLUE}Step 1: Checking Homebrew${NC}"
    check_homebrew
    
    echo -e "\n${BLUE}Step 2: Installing Colima${NC}"
    install_colima
    
    echo -e "\n${BLUE}Step 3: Starting Colima${NC}"
    start_colima
    
    echo -e "\n${BLUE}Step 4: Testing Docker${NC}"
    if test_docker; then
        echo -e "\n${GREEN}🎉 Colima setup complete!${NC}"
        echo -e "${YELLOW}You can now use Docker commands normally${NC}"
        echo -e "${YELLOW}To stop Colima: colima stop${NC}"
        echo -e "${YELLOW}To start Colima: colima start${NC}"
    else
        echo -e "\n${RED}❌ Setup failed${NC}"
        echo -e "${YELLOW}Try: colima restart${NC}"
    fi
else
    echo -e "${YELLOW}Colima installation cancelled${NC}"
fi