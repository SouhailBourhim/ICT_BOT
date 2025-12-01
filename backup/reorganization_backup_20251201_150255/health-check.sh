#!/bin/bash

# Health check script for RAG System Docker deployment
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏥 RAG System Health Check${NC}"
echo "=========================="

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $service_name... "
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"; then
        echo -e "${GREEN}✅ Healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ Unhealthy${NC}"
        return 1
    fi
}

# Function to check container status
check_container() {
    local container_name=$1
    
    echo -n "Checking container $container_name... "
    
    if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
        local status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-healthcheck")
        
        if [ "$status" = "healthy" ] || [ "$status" = "no-healthcheck" ]; then
            echo -e "${GREEN}✅ Running${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  Running but unhealthy (status: $status)${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Not running${NC}"
        return 1
    fi
}

# Check if Docker is running
echo -n "Checking Docker daemon... "
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Not running${NC}"
    exit 1
fi

echo

# Check containers
echo -e "${YELLOW}Container Status:${NC}"
check_container "rag-system-app" || CONTAINER_ISSUES=1
check_container "rag-system-ollama" || CONTAINER_ISSUES=1
check_container "rag-system-nginx" || NGINX_DOWN=1
check_container "rag-system-prometheus" || MONITORING_DOWN=1
check_container "rag-system-grafana" || MONITORING_DOWN=1

echo

# Check service endpoints
echo -e "${YELLOW}Service Health:${NC}"
check_service "RAG System" "http://localhost:8501/_stcore/health" || SERVICE_ISSUES=1
check_service "Ollama API" "http://localhost:11434/api/tags" || SERVICE_ISSUES=1

if [ -z "$NGINX_DOWN" ]; then
    check_service "Nginx" "http://localhost:80" || SERVICE_ISSUES=1
fi

if [ -z "$MONITORING_DOWN" ]; then
    check_service "Prometheus" "http://localhost:9090/-/healthy" || SERVICE_ISSUES=1
    check_service "Grafana" "http://localhost:3000/api/health" || SERVICE_ISSUES=1
fi

echo

# Check disk space
echo -e "${YELLOW}System Resources:${NC}"
echo -n "Checking disk space... "
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 90 ]; then
    echo -e "${GREEN}✅ OK (${DISK_USAGE}% used)${NC}"
else
    echo -e "${RED}❌ Low disk space (${DISK_USAGE}% used)${NC}"
    RESOURCE_ISSUES=1
fi

# Check memory usage
echo -n "Checking memory usage... "
if command -v free > /dev/null; then
    MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$MEMORY_USAGE" -lt 90 ]; then
        echo -e "${GREEN}✅ OK (${MEMORY_USAGE}% used)${NC}"
    else
        echo -e "${RED}❌ High memory usage (${MEMORY_USAGE}% used)${NC}"
        RESOURCE_ISSUES=1
    fi
else
    echo -e "${YELLOW}⚠️  Cannot check (free command not available)${NC}"
fi

# Check Docker volumes
echo -n "Checking Docker volumes... "
VOLUMES=$(docker volume ls -q | grep -E "(rag_data|rag_cache|rag_logs|ollama_data)" | wc -l)
if [ "$VOLUMES" -ge 4 ]; then
    echo -e "${GREEN}✅ OK ($VOLUMES volumes found)${NC}"
else
    echo -e "${YELLOW}⚠️  Some volumes missing ($VOLUMES/4 found)${NC}"
    VOLUME_ISSUES=1
fi

echo

# Summary
echo -e "${YELLOW}Health Check Summary:${NC}"
if [ -z "$CONTAINER_ISSUES" ] && [ -z "$SERVICE_ISSUES" ] && [ -z "$RESOURCE_ISSUES" ] && [ -z "$VOLUME_ISSUES" ]; then
    echo -e "${GREEN}🎉 All systems healthy!${NC}"
    echo
    echo -e "${BLUE}🌐 Access your services:${NC}"
    echo "📚 RAG System:      http://localhost:8501"
    echo "🤖 Ollama API:      http://localhost:11434"
    echo "📊 Grafana:         http://localhost:3000"
    echo "📈 Prometheus:      http://localhost:9090"
    exit 0
else
    echo -e "${RED}⚠️  Some issues detected!${NC}"
    echo
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    
    if [ ! -z "$CONTAINER_ISSUES" ]; then
        echo "• Check container logs: docker-compose logs"
        echo "• Restart containers: ./start-docker.sh"
    fi
    
    if [ ! -z "$SERVICE_ISSUES" ]; then
        echo "• Wait a few minutes for services to start"
        echo "• Check service logs for errors"
    fi
    
    if [ ! -z "$RESOURCE_ISSUES" ]; then
        echo "• Free up disk space or memory"
        echo "• Consider scaling down services"
    fi
    
    if [ ! -z "$VOLUME_ISSUES" ]; then
        echo "• Recreate volumes: docker-compose down -v && docker-compose up -d"
    fi
    
    exit 1
fi