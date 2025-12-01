#!/bin/bash

# Quick start script for RAG System Docker deployment
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="deployment/docker/docker-compose.yml"

echo -e "${BLUE}🚀 RAG System Docker Deployment${NC}"
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

# Function to show menu
show_menu() {
    echo -e "\n${YELLOW}Choose deployment option:${NC}"
    echo "1) 🏗️  Build and start full stack (recommended)"
    echo "2) 🚀 Start existing containers"
    echo "3) 🛑 Stop all containers"
    echo "4) 🔄 Restart all containers"
    echo "5) 📊 Show container status"
    echo "6) 📝 Show logs"
    echo "7) 🧹 Clean up (remove containers and volumes)"
    echo "8) ❌ Exit"
    echo
}

# Function to build and start
build_and_start() {
    echo -e "\n${YELLOW}Building and starting RAG System...${NC}"
    
    # Build the main application image
    echo -e "${YELLOW}Step 1: Building application image...${NC}"
    ./build-docker.sh
    
    # Start all services
    echo -e "\n${YELLOW}Step 2: Starting all services...${NC}"
    cd deployment/docker
    docker-compose up -d
    
    echo -e "\n${GREEN}✅ RAG System started successfully!${NC}"
    show_services
}

# Function to start existing containers
start_containers() {
    echo -e "\n${YELLOW}Starting existing containers...${NC}"
    cd deployment/docker
    docker-compose up -d
    echo -e "\n${GREEN}✅ Containers started!${NC}"
    show_services
}

# Function to stop containers
stop_containers() {
    echo -e "\n${YELLOW}Stopping all containers...${NC}"
    cd deployment/docker
    docker-compose down
    echo -e "\n${GREEN}✅ All containers stopped!${NC}"
}

# Function to restart containers
restart_containers() {
    echo -e "\n${YELLOW}Restarting all containers...${NC}"
    cd deployment/docker
    docker-compose restart
    echo -e "\n${GREEN}✅ All containers restarted!${NC}"
    show_services
}

# Function to show container status
show_status() {
    echo -e "\n${YELLOW}Container Status:${NC}"
    cd deployment/docker
    docker-compose ps
}

# Function to show logs
show_logs() {
    echo -e "\n${YELLOW}Recent logs (press Ctrl+C to exit):${NC}"
    cd deployment/docker
    docker-compose logs -f --tail=50
}

# Function to clean up
cleanup() {
    echo -e "\n${RED}⚠️  This will remove all containers and volumes!${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "\n${YELLOW}Cleaning up...${NC}"
        cd deployment/docker
        docker-compose down -v --remove-orphans
        docker system prune -f
        echo -e "\n${GREEN}✅ Cleanup completed!${NC}"
    else
        echo -e "\n${BLUE}Cleanup cancelled.${NC}"
    fi
}

# Function to show service URLs
show_services() {
    echo -e "\n${GREEN}🌐 Service URLs:${NC}"
    echo "📚 RAG System:      http://localhost:8501"
    echo "🤖 Ollama API:      http://localhost:11434"
    echo "📊 Grafana:         http://localhost:3000 (admin/admin123)"
    echo "📈 Prometheus:      http://localhost:9090"
    echo "🌐 Nginx (if SSL):  https://localhost"
    echo
    echo -e "${BLUE}💡 Tip: Wait 1-2 minutes for all services to be fully ready${NC}"
}

# Main menu loop
while true; do
    show_menu
    read -p "Enter your choice (1-8): " choice
    
    case $choice in
        1)
            build_and_start
            ;;
        2)
            start_containers
            ;;
        3)
            stop_containers
            ;;
        4)
            restart_containers
            ;;
        5)
            show_status
            ;;
        6)
            show_logs
            ;;
        7)
            cleanup
            ;;
        8)
            echo -e "\n${BLUE}👋 Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}❌ Invalid option. Please choose 1-8.${NC}"
            ;;
    esac
    
    echo
    read -p "Press Enter to continue..."
done