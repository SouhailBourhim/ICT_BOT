# RAG System Administration Guide

This guide provides comprehensive information for system administrators managing the RAG educational assistant system.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Installation and Setup](#installation-and-setup)
3. [Configuration Management](#configuration-management)
4. [User Management](#user-management)
5. [Document Management](#document-management)
6. [Performance Monitoring](#performance-monitoring)
7. [Maintenance Tasks](#maintenance-tasks)
8. [Security Management](#security-management)
9. [Backup and Recovery](#backup-and-recovery)
10. [Troubleshooting](#troubleshooting)

## System Architecture

### Component Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Query Processor │    │ Document Store  │
│   (Streamlit)   │◄──►│   & Enhancer    │◄──►│   (ChromaDB)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Conversation    │    │ Hybrid Retriever│    │ Metadata Store  │
│ Manager         │    │ (Vector + BM25) │    │   (SQLite)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Response        │    │ Language Model  │    │ Analytics &     │
│ Generator       │    │   (Ollama)      │    │ Monitoring      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Components

1. **Web Interface**: Streamlit-based user interface
2. **Query Processing**: Enhanced query understanding and expansion
3. **Retrieval System**: Hybrid semantic and keyword search
4. **Language Model**: Ollama-based response generation
5. **Document Processing**: Semantic chunking and metadata extraction
6. **Conversation Management**: Context-aware dialogue handling
7. **Analytics**: Performance monitoring and usage analytics
8. **Caching**: Multi-level caching for performance optimization

## Installation and Setup

### Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- 8GB+ RAM, 50GB+ storage
- Docker and Docker Compose
- SSL certificates (for production)

### Automated Installation

```bash
# Clone repository
git clone <repository-url>
cd rag-system

# Run setup script
sudo ./deployment/scripts/setup.sh

# Deploy with Docker Compose
./deployment/scripts/deploy.sh --environment production
```

### Manual Installation Steps

1. **System Dependencies**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip sqlite3 nginx certbot
   ```

2. **Application Setup**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Database Initialization**
   ```bash
   python3 -c "from core.system import RAGSystem; RAGSystem().initialize_database()"
   ```

4. **Ollama Installation**
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   sudo systemctl enable ollama
   sudo systemctl start ollama
   ollama pull llama2:7b-chat
   ollama pull nomic-embed-text
   ```

## Configuration Management

### Environment Configuration

Main configuration file: `.env`

```bash
# Environment Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# Database Configuration
DATABASE_URL=sqlite:///data/rag_system.db
DATABASE_POOL_SIZE=20
DATABASE_TIMEOUT=30

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:7b-chat
OLLAMA_TIMEOUT=120
EMBEDDING_MODEL=nomic-embed-text

# Application Settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
MAX_UPLOAD_SIZE=200
SESSION_TIMEOUT=3600

# Cache Configuration
CACHE_DIR=cache
MEMORY_CACHE_SIZE=1000
DISK_CACHE_SIZE_MB=500
CACHE_TTL=3600

# Security Settings
SECRET_KEY=your-secure-secret-key
ALLOWED_HOSTS=localhost,your-domain.com
RATE_LIMIT_PER_MINUTE=60
MAX_CONCURRENT_USERS=50

# Monitoring
ENABLE_ANALYTICS=true
METRICS_RETENTION_DAYS=30
LOG_RETENTION_DAYS=7
```

### Advanced Configuration

#### Database Optimization
```bash
# config/database.py
DATABASE_CONFIG = {
    'sqlite': {
        'journal_mode': 'WAL',
        'synchronous': 'NORMAL',
        'cache_size': 10000,
        'temp_store': 'MEMORY',
        'mmap_size': 268435456  # 256MB
    }
}
```

#### Caching Configuration
```bash
# config/cache.py
CACHE_CONFIG = {
    'memory': {
        'max_size': 1000,
        'ttl_seconds': 1800
    },
    'disk': {
        'max_size_mb': 500,
        'ttl_seconds': 86400
    }
}
```

## User Management

### User Authentication (if enabled)

#### Adding Users
```bash
# Add new user
python3 manage_users.py add --username student1 --email student1@inpt.ac.ma --role student

# Add administrator
python3 manage_users.py add --username admin1 --email admin@inpt.ac.ma --role admin
```

#### User Roles
- **Student**: Basic access to query system
- **Instructor**: Access to analytics and user management
- **Admin**: Full system access and configuration

#### Session Management
```bash
# View active sessions
python3 manage_users.py sessions --list

# Terminate user session
python3 manage_users.py sessions --terminate --user student1

# Clear all sessions
python3 manage_users.py sessions --clear-all
```

### Usage Analytics

#### User Activity Monitoring
```bash
# View user statistics
python3 analytics.py --user-stats --days 30

# Export usage report
python3 analytics.py --export --format csv --output usage_report.csv
```

## Document Management

### Document Ingestion

#### Bulk Document Upload
```bash
# Process all documents in data directory
python3 ingest_enhanced.py --directory data/ --recursive

# Process specific document types
python3 ingest_enhanced.py --directory data/ --types pdf,docx

# Process with specific course module
python3 ingest_enhanced.py --file document.pdf --module "Wireless Communications"
```

#### Document Processing Options
```bash
# Force reprocessing
python3 ingest_enhanced.py --force-reprocess

# Skip existing documents
python3 ingest_enhanced.py --skip-existing

# Validate documents only
python3 ingest_enhanced.py --validate-only
```

### Document Organization

#### Automatic Classification
Documents are automatically classified by:
- Course module (based on content analysis)
- Document type (PDF, DOCX, TXT)
- Language (French, English, multilingual)
- Difficulty level (beginner, intermediate, advanced)

#### Manual Document Management
```bash
# List all documents
python3 manage_docs.py --list

# Update document metadata
python3 manage_docs.py --update --id doc123 --module "Advanced Topics"

# Remove document
python3 manage_docs.py --remove --id doc123

# Reindex document
python3 manage_docs.py --reindex --id doc123
```

### Content Quality Control

#### Document Validation
```bash
# Validate document quality
python3 validate_docs.py --check-quality

# Check for duplicates
python3 validate_docs.py --check-duplicates

# Verify citations and references
python3 validate_docs.py --check-references
```

## Performance Monitoring

### System Metrics

#### Real-time Monitoring
```bash
# System health check
python3 health_check.py

# Performance metrics
python3 metrics.py --realtime

# Resource usage
python3 metrics.py --resources
```

#### Key Performance Indicators
- Query response time (target: <3 seconds)
- System availability (target: >99.5%)
- Concurrent user capacity (target: 50+ users)
- Memory usage (target: <80% of available)
- Disk usage (target: <90% of available)

### Application Monitoring

#### Query Performance
```bash
# Analyze slow queries
python3 analyze_performance.py --slow-queries --threshold 5

# Query success rate
python3 analyze_performance.py --success-rate --days 7

# Popular queries
python3 analyze_performance.py --popular-queries --limit 20
```

#### Error Monitoring
```bash
# View error logs
tail -f logs/rag_system.log | grep ERROR

# Error statistics
python3 analyze_errors.py --stats --days 7

# Error alerts
python3 analyze_errors.py --alerts --email admin@inpt.ac.ma
```

### Grafana Dashboard

Access monitoring dashboard at `http://localhost:3000`

Key dashboards:
- **System Overview**: CPU, memory, disk usage
- **Application Metrics**: Query rates, response times
- **User Activity**: Active users, popular queries
- **Error Tracking**: Error rates, failure patterns

## Maintenance Tasks

### Daily Tasks

#### Automated Daily Maintenance
```bash
# Create daily maintenance script
cat > /etc/cron.daily/rag-system-maintenance << 'EOF'
#!/bin/bash
cd /opt/rag-system

# Check system health
python3 health_check.py --alert-on-failure

# Optimize database
python3 -c "from utils.database_optimizer import DatabaseOptimizer; DatabaseOptimizer('data/rag_system.db').optimize_database()"

# Clear old logs
find logs/ -name "*.log" -mtime +7 -delete

# Clear old cache files
find cache/ -name "*" -mtime +1 -delete

# Generate daily report
python3 generate_report.py --daily --email admin@inpt.ac.ma
EOF

chmod +x /etc/cron.daily/rag-system-maintenance
```

### Weekly Tasks

#### Database Maintenance
```bash
# Weekly database optimization
python3 -c "
from utils.database_optimizer import DatabaseOptimizer
optimizer = DatabaseOptimizer('data/rag_system.db')
optimizer.optimize_database()
print('Database optimization completed')
"

# Backup database
sqlite3 data/rag_system.db ".backup backups/weekly_backup_$(date +%Y%m%d).db"

# Analyze database statistics
python3 -c "
from utils.database_optimizer import DatabaseOptimizer
optimizer = DatabaseOptimizer('data/rag_system.db')
stats = optimizer.get_database_stats()
print('Database Statistics:', stats)
"
```

#### Performance Analysis
```bash
# Weekly performance report
python3 analyze_performance.py --weekly-report --output reports/

# Cache performance analysis
python3 -c "
from utils.caching import get_cache
cache = get_cache()
stats = cache.stats()
print('Cache Statistics:', stats)
"
```

### Monthly Tasks

#### System Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python dependencies
source .venv/bin/activate
pip list --outdated
pip install -r requirements.txt --upgrade

# Update Ollama models
ollama pull llama2:7b-chat
ollama pull nomic-embed-text
```

#### Security Audit
```bash
# Run security scan
bandit -r . -f json -o security_report.json

# Check for vulnerabilities
pip-audit

# Review access logs
python3 analyze_security.py --access-logs --suspicious
```

## Security Management

### Access Control

#### Network Security
```bash
# Configure firewall
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8501/tcp   # Block direct app access

# Rate limiting with nginx
# Already configured in nginx.conf
```

#### Application Security
```bash
# Enable security headers
# Configured in nginx.conf:
# - X-Frame-Options: DENY
# - X-Content-Type-Options: nosniff
# - X-XSS-Protection: 1; mode=block
# - Strict-Transport-Security

# Input validation
# Implemented in application code
```

### SSL/TLS Management

#### Certificate Management
```bash
# Renew Let's Encrypt certificates
sudo certbot renew --dry-run

# Auto-renewal setup
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### Security Monitoring

#### Log Analysis
```bash
# Monitor failed login attempts
grep "Failed login" logs/rag_system.log

# Check for suspicious activity
python3 security_monitor.py --analyze-logs --alert-threshold 10

# Generate security report
python3 security_monitor.py --report --days 30
```

## Backup and Recovery

### Backup Strategy

#### Automated Backups
```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/rag-system"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Backup database
sqlite3 data/rag_system.db ".backup $BACKUP_DIR/$DATE/rag_system.db"

# Backup configuration
cp .env "$BACKUP_DIR/$DATE/"
cp -r config/ "$BACKUP_DIR/$DATE/"

# Backup documents (if needed)
tar -czf "$BACKUP_DIR/$DATE/documents.tar.gz" data/

# Backup logs
tar -czf "$BACKUP_DIR/$DATE/logs.tar.gz" logs/

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR/$DATE"
EOF

chmod +x backup.sh

# Schedule daily backups
echo "0 2 * * * /opt/rag-system/backup.sh" | crontab -
```

### Disaster Recovery

#### Recovery Procedures
```bash
# 1. Stop services
docker-compose down

# 2. Restore database
cp backups/latest/rag_system.db data/

# 3. Restore configuration
cp backups/latest/.env .
cp -r backups/latest/config/ .

# 4. Restart services
docker-compose up -d

# 5. Verify system health
python3 health_check.py
```

#### Recovery Testing
```bash
# Monthly recovery test
python3 test_recovery.py --simulate-failure --test-restore
```

## Troubleshooting

### Common Issues

#### 1. High Memory Usage
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Restart services to clear memory
docker-compose restart

# Optimize cache settings
# Reduce MEMORY_CACHE_SIZE in .env
```

#### 2. Slow Query Performance
```bash
# Analyze slow queries
python3 analyze_performance.py --slow-queries

# Optimize database
python3 -c "from utils.database_optimizer import DatabaseOptimizer; DatabaseOptimizer('data/rag_system.db').optimize_database()"

# Clear caches
python3 -c "from utils.caching import clear_all_caches; clear_all_caches()"
```

#### 3. Ollama Connection Issues
```bash
# Check Ollama status
sudo systemctl status ollama

# Restart Ollama
sudo systemctl restart ollama

# Test Ollama API
curl http://localhost:11434/api/tags

# Check Ollama logs
journalctl -u ollama -f
```

#### 4. Database Lock Issues
```bash
# Check for database locks
lsof data/rag_system.db

# Kill processes holding locks
sudo kill -9 <process_id>

# Repair database if needed
sqlite3 data/rag_system.db "PRAGMA integrity_check;"
```

### Log Analysis

#### Application Logs
```bash
# View recent errors
tail -f logs/rag_system.log | grep ERROR

# Search for specific issues
grep "timeout" logs/rag_system.log
grep "connection" logs/rag_system.log

# Analyze log patterns
python3 analyze_logs.py --pattern-analysis --days 7
```

#### System Logs
```bash
# Docker container logs
docker-compose logs -f rag-system

# System service logs
journalctl -u rag-system -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Performance Optimization

#### Database Optimization
```bash
# Run database analysis
python3 -c "
from utils.database_optimizer import DatabaseOptimizer
optimizer = DatabaseOptimizer('data/rag_system.db')
optimizer.analyze_query_performance('SELECT * FROM conversations LIMIT 10')
"

# Optimize indexes
python3 -c "
from utils.database_optimizer import DatabaseOptimizer
optimizer = DatabaseOptimizer('data/rag_system.db')
optimizer.create_indexes()
"
```

#### Cache Optimization
```bash
# Analyze cache performance
python3 -c "
from utils.caching import get_cache
cache = get_cache()
stats = cache.stats()
print('Hit rate:', stats['memory']['hit_rate'])
print('Cache size:', stats['memory']['size'])
"

# Warm up caches
python3 -c "
from utils.caching import CacheWarmer, get_cache
from managers.conversation_manager import ConversationManager
warmer = CacheWarmer(get_cache())
warmer.warm_conversation_cache(ConversationManager())
"
```

### Emergency Procedures

#### System Recovery
```bash
# Emergency restart
docker-compose down
docker-compose up -d

# Reset to known good state
git checkout main
./deployment/scripts/deploy.sh --environment production --fresh

# Restore from backup
./restore_backup.sh backups/latest/
```

#### Contact Information
- **System Administrator**: admin@inpt.ac.ma
- **Technical Support**: support@inpt.ac.ma
- **Emergency Contact**: +212-xxx-xxx-xxx

This administration guide provides comprehensive information for managing the RAG system. Regular monitoring, maintenance, and following these procedures will ensure optimal system performance and reliability.