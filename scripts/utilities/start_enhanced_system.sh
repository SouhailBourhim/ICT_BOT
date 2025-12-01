#!/bin/bash
# Enhanced RAG System Startup Script

echo "🚀 Starting Enhanced RAG System..."

# Check environment
if [ -f "config/environments/${ENVIRONMENT:-development}.env" ]; then
    echo "📋 Loading environment: ${ENVIRONMENT:-development}"
    source "config/environments/${ENVIRONMENT:-development}.env"
fi

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
fi

# Set default environment variables if not set
export OLLAMA_MODEL=${OLLAMA_MODEL:-"llama3"}
export CHROMA_PATH=${CHROMA_PATH:-"chroma"}
export DEFAULT_K=${DEFAULT_K:-"5"}
export ENABLE_ENHANCED_FEATURES=${ENABLE_ENHANCED_FEATURES:-"true"}
export SIMILARITY_THRESHOLD=${SIMILARITY_THRESHOLD:-"0.7"}
export MAX_TOKENS=${MAX_TOKENS:-"4096"}
export TEMPERATURE=${TEMPERATURE:-"0.1"}

# Ensure required directories exist
mkdir -p data logs config/profiles backup

# Run health check
echo "🔍 Running system health check..."
python -c "
try:
    from core.system import RAGSystem
    from config.settings import get_settings
    
    # Test configuration
    config = get_settings()
    print('✅ Configuration loaded successfully')
    
    # Test system initialization
    system = RAGSystem()
    print('✅ System initialized successfully')
    
    print('🎉 System health check passed!')
except Exception as e:
    print(f'⚠️  Health check warning: {e}')
    print('🔄 Continuing with startup (graceful degradation enabled)...')
"

# Check if Ollama is running
echo "🤖 Checking Ollama service..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "⚠️  Ollama not detected. Please ensure Ollama is running:"
    echo "   - Install: https://ollama.ai"
    echo "   - Start: ollama serve"
    echo "   - Pull model: ollama pull ${OLLAMA_MODEL}"
fi

# Start the application
echo "🌐 Starting Streamlit application..."
echo "📍 Access the application at: http://localhost:${PORT:-8501}"
echo "🔧 Enhanced mode: ${ENABLE_ENHANCED_FEATURES}"
echo ""

streamlit run app.py \
    --server.port ${PORT:-8501} \
    --server.address ${HOST:-0.0.0.0} \
    --server.headless true \
    --browser.gatherUsageStats false