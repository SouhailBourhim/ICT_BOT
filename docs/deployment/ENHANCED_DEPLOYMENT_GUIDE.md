# Enhanced RAG System Deployment Guide

This guide covers the deployment of the enhanced RAG system with all new features and capabilities.

## Overview

The enhanced RAG system includes:
- Advanced document processing with semantic chunking
- Hybrid retrieval combining semantic and keyword search
- Conversation memory and context management
- Query enhancement and spell correction
- Response attribution and confidence scoring
- Performance monitoring and analytics
- Enhanced user interface with filters and auto-complete

## Prerequisites

### System Requirements
- Python 3.8 or higher
- 8GB RAM minimum (16GB recommended)
- 10GB free disk space
- Ollama installed and running
- SQLite 3.35 or higher

### Dependencies
```bash
pip install -r requirements.txt
```

### Environment Setup
```bash
# Create necessary directories
mkdir -p data logs config/profiles backup

# Set environment variables
export OLLAMA_MODEL="llama3"
export CHROMA_PATH="chroma"
export LOG_LEVEL="INFO"
export ENABLE_ENHANCED_FEATURES="true"
```

## Installation Steps

### 1. Clone and Setup
```bash
git clone <repository-url>
cd rag-system-enhanced
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copy environment template
cp config/.env.example .env

# Edit configuration
nano .env
```

Key configuration variables:
```env
# Core Configuration
OLLAMA_MODEL=llama3
CHROMA_PATH=chroma
DEFAULT_K=5
SIMILARITY_THRESHOLD=0.7

# Enhanced Features
ENABLE_CONVERSATION_MEMORY=true
ENABLE_HYBRID_SEARCH=true
ENABLE_QUERY_ENHANCEMENT=true
ENABLE_SOURCE_ATTRIBUTION=true
ENABLE_PERFORMANCE_MONITORING=true

# Database Paths
METADATA_DB_PATH=data/metadata.db
CONVERSATION_DB_PATH=data/conversations.db
ANALYTICS_DB_PATH=data/analytics.db

# Performance Settings
ENABLE_CACHING=true
CACHE_TTL_SECONDS=3600
MAX_CONCURRENT_REQUESTS=10
```

### 3. Database Migration (if upgrading)
```bash
# Run migration script
python migration_scripts/migrate_to_enhanced.py

# Verify migration
python migration_scripts/migrate_to_enhanced.py --verify-only
```

### 4. Document Ingestion
```bash
# Enhanced ingestion with new features
python ingest_enhanced.py --input-dir data --batch-size 10

# Or use legacy ingestion for compatibility
python ingest.py
```

### 5. System Initialization
```bash
# Initialize enhanced system
python -c "
from core.system import RAGSystem
system = RAGSystem()
system.initialize()
print('System initialized successfully')
"
```

## Deployment Options

### Option 1: Local Development
```bash
# Start the application
streamlit run app.py --server.port 8501
```

### Option 2: Docker Deployment
```bash
# Build Docker image
docker build -t rag-system-enhanced -f deployment/docker/Dockerfile .

# Run with docker-compose
cd deployment/docker
docker-compose up -d
```

### Option 3: Production Deployment
```bash
# Use deployment script
chmod +x deployment/scripts/deploy.sh
./deployment/scripts/deploy.sh production
```

## Configuration Management

### Feature Profiles
Create different feature profiles for different environments:

```bash
# Create development profile
python -c "
from config.enhanced_config import get_enhanced_config
config = get_enhanced_config()
config.create_feature_profile('development', {
    'enable_conversation_memory': True,
    'enable_query_analytics': True,
    'enable_performance_monitoring': False
})
"

# Load profile
python -c "
from config.enhanced_config import get_enhanced_config
config = get_enhanced_config()
config.load_feature_profile('development')
config.save_to_file()
"
```

### Environment-Specific Configuration

#### Development
```env
LOG_LEVEL=DEBUG
ENABLE_PERFORMANCE_MONITORING=false
ENABLE_QUERY_ANALYTICS=false
MAX_CONCURRENT_REQUESTS=5
```

#### Staging
```env
LOG_LEVEL=INFO
ENABLE_PERFORMANCE_MONITORING=true
ENABLE_QUERY_ANALYTICS=true
MAX_CONCURRENT_REQUESTS=10
```

#### Production
```env
LOG_LEVEL=WARNING
ENABLE_PERFORMANCE_MONITORING=true
ENABLE_QUERY_ANALYTICS=true
ENABLE_CACHING=true
MAX_CONCURRENT_REQUESTS=20
```

## Health Monitoring

### System Health Check
```bash
# Check system health
python -c "
from core.system import RAGSystem
system = RAGSystem()
health = system.health_check()
print(f'System Status: {health[\"overall_status\"]}')
"
```

### Performance Monitoring
The system includes built-in performance monitoring:
- Query response times
- System resource usage
- Error rates and types
- User interaction patterns

Access monitoring dashboard at: `http://localhost:8501/monitoring`

## Backup and Recovery

### Automated Backup
```bash
# Create backup script
cat > backup_system.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup databases
cp -r chroma "$BACKUP_DIR/"
cp data/*.db "$BACKUP_DIR/"
cp -r config "$BACKUP_DIR/"

echo "Backup created: $BACKUP_DIR"
EOF

chmod +x backup_system.sh
```

### Recovery Process
```bash
# Restore from backup
BACKUP_DIR="backup/20240101_120000"
cp -r "$BACKUP_DIR/chroma" .
cp "$BACKUP_DIR"/*.db data/
cp -r "$BACKUP_DIR/config" .

# Restart system
systemctl restart rag-system
```

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Issues
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Restart Ollama
systemctl restart ollama
```

#### 2. Database Connection Issues
```bash
# Check database permissions
ls -la data/
chmod 664 data/*.db

# Recreate databases
python migration_scripts/migrate_to_enhanced.py --no-backup
```

#### 3. Memory Issues
```bash
# Monitor memory usage
python -c "
from utils.health_monitor import HealthMonitor
monitor = HealthMonitor()
status = monitor.get_system_metrics()
print(f'Memory Usage: {status[\"memory_usage_percent\"]}%')
"

# Adjust chunk sizes if needed
export MIN_CHUNK_SIZE=300
export MAX_CHUNK_SIZE=1500
```

#### 4. Performance Issues
```bash
# Enable caching
export ENABLE_CACHING=true

# Reduce concurrent requests
export MAX_CONCURRENT_REQUESTS=5

# Optimize database
python -c "
from utils.database_optimizer import DatabaseOptimizer
optimizer = DatabaseOptimizer()
optimizer.optimize_all_databases()
"
```

### Log Analysis
```bash
# View system logs
tail -f logs/rag_system.log

# Filter error logs
grep "ERROR" logs/rag_system.log

# Monitor performance logs
grep "PERFORMANCE" logs/rag_system.log
```

## Security Considerations

### Access Control
- Configure firewall rules for port 8501
- Use reverse proxy (nginx) for production
- Enable HTTPS with SSL certificates
- Implement rate limiting

### Data Protection
- Encrypt sensitive configuration files
- Regular security updates
- Monitor access logs
- Backup encryption

### Example nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Scaling Considerations

### Horizontal Scaling
- Use load balancer for multiple instances
- Shared database configuration
- Session management with Redis
- Container orchestration with Kubernetes

### Vertical Scaling
- Increase memory allocation
- Optimize chunk processing
- Database indexing optimization
- Caching layer enhancement

## Maintenance

### Regular Tasks
```bash
# Weekly maintenance script
cat > weekly_maintenance.sh << 'EOF'
#!/bin/bash

# Clean old logs
find logs/ -name "*.log" -mtime +30 -delete

# Optimize databases
python -c "from utils.database_optimizer import DatabaseOptimizer; DatabaseOptimizer().optimize_all_databases()"

# Update analytics
python -c "from managers.analytics_manager import AnalyticsManager; AnalyticsManager().generate_weekly_report()"

# Health check
python -c "from core.system import RAGSystem; print(RAGSystem().health_check())"
EOF

chmod +x weekly_maintenance.sh
```

### Updates and Upgrades
```bash
# Update system
git pull origin main
pip install -r requirements.txt

# Run migration if needed
python migration_scripts/migrate_to_enhanced.py --verify-only

# Restart services
systemctl restart rag-system
```

## Support and Documentation

### Additional Resources
- [User Guide](USER_GUIDE.md)
- [Admin Guide](ADMIN_GUIDE.md)
- [API Documentation](API_DOCUMENTATION.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

### Getting Help
- Check system logs first
- Review configuration settings
- Test with minimal configuration
- Contact support with log files and configuration details

## Performance Benchmarks

### Expected Performance
- Query response time: < 2 seconds
- Document ingestion: 10-50 docs/minute
- Memory usage: 2-4GB typical
- Concurrent users: 10-20 (depending on hardware)

### Optimization Tips
1. Enable caching for frequently accessed data
2. Use appropriate chunk sizes for your documents
3. Monitor and tune database indexes
4. Implement connection pooling
5. Use SSD storage for databases
6. Optimize Ollama model selection

This deployment guide should help you successfully deploy and maintain the enhanced RAG system in various environments.