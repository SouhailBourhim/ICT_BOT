#!/bin/bash

# Setup script for Docker-based ingestion
# This script prepares the environment for document ingestion on a high-memory machine

set -e

echo "🚀 Setting up Docker-based RAG ingestion environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p deployment/docker/documents
mkdir -p deployment/docker/export
mkdir -p logs

# Set permissions
chmod +x scripts/export_ingestion_data.py
chmod +x scripts/import_ingestion_data.py

echo "📋 Directory structure created:"
echo "  deployment/docker/documents/ - Place your documents here"
echo "  deployment/docker/export/    - Export packages will be created here"
echo "  logs/                       - Ingestion logs"

# Check system resources
echo ""
echo "💻 System Resources:"
echo "  RAM: $(free -h | awk '/^Mem:/ {print $2}' 2>/dev/null || echo 'Unable to detect')"
echo "  Disk: $(df -h . | awk 'NR==2 {print $4}' 2>/dev/null || echo 'Unable to detect') available"
echo "  CPU: $(nproc 2>/dev/null || echo 'Unable to detect') cores"

# Recommend settings based on available RAM
if command -v free &> /dev/null; then
    RAM_GB=$(free -g | awk '/^Mem:/ {print $2}')
    echo ""
    echo "📊 Recommended settings for your system:"
    
    if [ "$RAM_GB" -ge 16 ]; then
        echo "  ✅ 16GB+ RAM detected - You can use default settings"
        echo "  Recommended: BATCH_SIZE=5, MAX_CHUNK_SIZE=1500"
    elif [ "$RAM_GB" -ge 8 ]; then
        echo "  ⚠️  8-16GB RAM detected - Use conservative settings"
        echo "  Recommended: BATCH_SIZE=2, MAX_CHUNK_SIZE=1000"
        
        # Update ingestion.env with conservative settings
        sed -i 's/BATCH_SIZE=3/BATCH_SIZE=2/' deployment/docker/ingestion.env 2>/dev/null || true
        sed -i 's/MAX_CHUNK_SIZE=1500/MAX_CHUNK_SIZE=1000/' deployment/docker/ingestion.env 2>/dev/null || true
        echo "  ✅ Updated ingestion.env with conservative settings"
    else
        echo "  ❌ Less than 8GB RAM detected - Ingestion may fail"
        echo "  Consider using a machine with more RAM or processing documents in very small batches"
    fi
fi

echo ""
echo "🔧 Next steps:"
echo ""
echo "1. Copy your documents to the documents directory:"
echo "   cp /path/to/your/documents/* deployment/docker/documents/"
echo ""
echo "2. Review and adjust ingestion settings if needed:"
echo "   nano deployment/docker/ingestion.env"
echo ""
echo "3. Start the ingestion process:"
echo "   cd deployment/docker"
echo "   docker-compose -f docker-compose.ingestion.yml up -d ollama-ingestion"
echo "   docker exec rag-ingestion-ollama ollama pull llama3"
echo "   docker-compose -f docker-compose.ingestion.yml up rag-ingestion"
echo ""
echo "4. Monitor progress:"
echo "   docker-compose -f docker-compose.ingestion.yml logs -f rag-ingestion"
echo ""
echo "5. Export processed data:"
echo "   docker-compose -f docker-compose.ingestion.yml --profile export up data-exporter"
echo ""
echo "📖 For detailed instructions, see: docs/deployment/DOCKER_INGESTION_GUIDE.md"

# Check if documents directory is empty
if [ -z "$(ls -A deployment/docker/documents 2>/dev/null)" ]; then
    echo ""
    echo "⚠️  The documents directory is empty. Don't forget to add your documents!"
else
    DOC_COUNT=$(ls -1 deployment/docker/documents | wc -l)
    echo ""
    echo "✅ Found $DOC_COUNT files in documents directory"
fi

echo ""
echo "🎉 Setup complete! Ready for ingestion."