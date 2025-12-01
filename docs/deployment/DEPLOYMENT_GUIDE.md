# RAG System Deployment Guide

This guide provides comprehensive instructions for deploying the RAG (Retrieval-Augmented Generation) educational assistant system in different environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Environment Setup](#environment-setup)
4. [Docker Deployment](#docker-deployment)
5. [Manual Deployment](#manual-deployment)
6. [Configuration](#configuration)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS (10.15+), or Windows 10+ with WSL2
- **Memory**: Minimum 4GB RAM, recommended 8GB+
- **Storage**: Minimum 10GB free space
- **CPU**: 2+ cores recommended
- **Network**: Internet connection for downloading models and dependencies

### Software Dependencies

- **Python**: 3.8 or higher
- **Docker**: 20.10+ (for containerized deployment)
- **Docker Compose**: 1.29+ (for multi-service deployment)
- **Git**: For cloning the repository
- **Ollama**: For running local language models

## Quick Start

### Automated Setup

The fastest way to get started is using the automated setup script:

```bash
# Clone the repository
git clone <repository-url>
cd rag-system

# Run the setup script
chmod +x deployment/scripts/setup.sh
./deployment/scripts/setup.sh
```

This script will:
- Check system requirements
- Install dependencies
- Set up Python virtual environment
- Initialize the database
- Install and configure Ollama
- Run verification tests

### Manual Quick Start

If you prefer manual setup:

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up configuration
cp config/.env.example .env
# Edit .env with your settings

# 4. Initialize database
python3 -c "from core.system import RAGSystem; RAGSystem().initialize_database()"

# 5. Start the application
streamlit run app.py
```

## Environment Setup

### Development Environment

For local development:

```bash
# Activate virtual environment
source .venv/bin/activate

# Install development dependencies
pip install pytest pytest-cov flake8 mypy black isort

# Run in development mode
export ENVIRONMENT=development
streamlit run app.py --server.port 8501
```

### Staging Environment

For staging deployment:

```bash
# Deploy to staging
./deployment/scripts/deploy.sh --environment staging

# Access staging application
open http://localhost:8502
```

### Production Environment

For production deployment:

```bash
# Deploy to production with fresh build
./deployment/scripts/deploy.sh --environment production --fresh

# Access production application
open http://localhost:8503
```

## Docker Deployment

### Single Container Deployment

For simple deployment with Docker:

```bash
# Build the image
docker build -t rag-system -f deployment/docker/Dockerfile .

# Run the container
docker run -d \
  --name rag-system \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  rag-system
```

### Multi-Service Deployment with Docker Compose

For full-featured deployment with all services:

```bash
# Start all services
docker-compose -f deployment/docker/docker-compose.yml up -d

# Check service status
docker-compose -f deployment/docker/docker-compose.yml ps

# View logs
docker-compose -f deployment/docker/docker-compose.yml logs -f
```

Services included:
- **rag-system**: Main application
- **ollama**: Language model service
- **nginx**: Reverse proxy and load balancer
- **prometheus**: Metrics collection
- **grafana**: Monitoring dashboard

### Service URLs

After deployment, access services at:
- **Application**: http://localhost (or https://localhost with SSL)
- **Grafana Dashboard**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Ollama API**: http://localhost:11434

## Manual Deployment

### Step-by-Step Manual Deployment

1. **Prepare the Environment**
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade -y
   
   # Install system dependencies
   sudo apt install -y python3 python3-pip python3-venv sqlite3 curl git
   ```

2. **Clone and Setup Application**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd rag-system
   
   # Create virtual environment
   python3 -m venv .venv
   source .venv/bin/activate
   
   # Install Python dependencies
   pip install -r requirements.txt
   ```

3. **Configure Application**
   ```bash
   # Copy configuration template
   cp config/.env.example .env
   
   # Edit configuration (see Configuration section)
   nano .env
   ```

4. **Initialize Database**
   ```bash
   # Create database and tables
   python3 -c "
   from core.system import RAGSystem
   system = RAGSystem()
   system.initialize_database()
   print('Database initialized')
   "
   ```

5. **Install and Configure Ollama**
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Start Ollama service
   sudo systemctl enable ollama
   sudo systemctl start ollama
   
   # Pull required models
   ollama pull llama2:7b-chat
   ollama pull nomic-embed-text
   ```

6. **Start Application**
   ```bash
   # Start with Streamlit
   streamlit run app.py --server.port 8501 --server.address 0.0.0.0
   
   # Or start with production server (gunicorn)
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8501 app:app
   ```

### Process Management with systemd

Create a systemd service for production:

```bash
# Create service file
sudo nano /etc/systemd/system/rag-system.service
```

```ini
[Unit]
Description=RAG System Educational Assistant
After=network.target

[Service]
Type=simple
User=raguser
WorkingDirectory=/opt/rag-system
Environment=PATH=/opt/rag-system/.venv/bin
ExecStart=/opt/rag-system/.venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable rag-system
sudo systemctl start rag-system
sudo systemctl status rag-system
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Environment
ENVIRONMENT=production  # development, staging, production
LOG_LEVEL=INFO         # DEBUG, INFO, WARNING, ERROR

# Database
DATABASE_URL=sqlite:///data/rag_system.db

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:7b-chat
EMBEDDING_MODEL=nomic-embed-text

# Application Settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
MAX_UPLOAD_SIZE=200  # MB

# Cache Settings
CACHE_DIR=cache
CACHE_TTL=3600      # seconds
MAX_CACHE_SIZE=1000 # items

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Database Configuration

For production, consider using PostgreSQL:

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE rag_system;
CREATE USER raguser WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE rag_system TO raguser;
\q

# Update .env
DATABASE_URL=postgresql://raguser:secure_password@localhost/rag_system
```

### SSL/TLS Configuration

For production deployment with SSL:

1. **Obtain SSL Certificates**
   ```bash
   # Using Let's Encrypt
   sudo apt install certbot
   sudo certbot certonly --standalone -d your-domain.com
   ```

2. **Configure Nginx**
   ```bash
   # Copy certificates to deployment directory
   sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deployment/ssl/cert.pem
   sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem deployment/ssl/key.pem
   ```

3. **Update Docker Compose**
   ```yaml
   # In docker-compose.yml, update nginx volumes
   volumes:
     - /etc/letsencrypt/live/your-domain.com:/etc/nginx/ssl:ro
   ```

## Monitoring and Maintenance

### Health Checks

The system includes built-in health checks:

```bash
# Check application health
curl http://localhost:8501/_stcore/health

# Check Ollama health
curl http://localhost:11434/api/tags

# Check system resources
docker stats
```

### Log Management

Logs are stored in multiple locations:

```bash
# Application logs
tail -f logs/rag_system.log

# Docker container logs
docker-compose logs -f rag-system

# System logs
journalctl -u rag-system -f
```

### Database Maintenance

Regular maintenance tasks:

```bash
# Backup database
sqlite3 data/rag_system.db ".backup backup_$(date +%Y%m%d).db"

# Optimize database
python3 -c "
from utils.database_optimizer import DatabaseOptimizer
optimizer = DatabaseOptimizer('data/rag_system.db')
optimizer.optimize_database()
"

# Check database statistics
python3 -c "
from utils.database_optimizer import DatabaseOptimizer
optimizer = DatabaseOptimizer('data/rag_system.db')
print(optimizer.get_database_stats())
"
```

### Performance Monitoring

Monitor system performance:

```bash
# Run performance tests
python3 run_tests.py --type performance

# Check cache statistics
python3 -c "
from utils.caching import get_cache
cache = get_cache()
print(cache.stats())
"

# Monitor resource usage
htop
iotop
```

### Updates and Upgrades

To update the system:

```bash
# 1. Backup data
./deployment/scripts/deploy.sh --environment production --backup-only

# 2. Pull latest code
git pull origin main

# 3. Update dependencies
source .venv/bin/activate
pip install -r requirements.txt --upgrade

# 4. Run database migrations (if any)
python3 migrate.py

# 5. Deploy updated version
./deployment/scripts/deploy.sh --environment production --fresh
```

## Troubleshooting

### Common Issues

1. **Application Won't Start**
   ```bash
   # Check logs
   docker-compose logs rag-system
   
   # Check port availability
   netstat -tlnp | grep 8501
   
   # Check virtual environment
   which python3
   pip list
   ```

2. **Ollama Connection Issues**
   ```bash
   # Check Ollama status
   systemctl status ollama
   
   # Test Ollama API
   curl http://localhost:11434/api/tags
   
   # Restart Ollama
   sudo systemctl restart ollama
   ```

3. **Database Issues**
   ```bash
   # Check database file permissions
   ls -la data/rag_system.db
   
   # Test database connection
   sqlite3 data/rag_system.db ".tables"
   
   # Repair database
   sqlite3 data/rag_system.db "PRAGMA integrity_check;"
   ```

4. **Memory Issues**
   ```bash
   # Check memory usage
   free -h
   
   # Check for memory leaks
   python3 run_tests.py --type load
   
   # Restart services
   docker-compose restart
   ```

5. **Performance Issues**
   ```bash
   # Check system resources
   htop
   iotop
   
   # Optimize database
   python3 -c "from utils.database_optimizer import DatabaseOptimizer; DatabaseOptimizer('data/rag_system.db').optimize_database()"
   
   # Clear caches
   python3 -c "from utils.caching import clear_all_caches; clear_all_caches()"
   ```

### Getting Help

If you encounter issues:

1. Check the logs for error messages
2. Review this troubleshooting section
3. Search existing issues in the repository
4. Create a new issue with:
   - System information
   - Error messages
   - Steps to reproduce
   - Log files

### Maintenance Schedule

Recommended maintenance schedule:

- **Daily**: Check logs and system health
- **Weekly**: Review performance metrics and optimize if needed
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Full system backup and disaster recovery test

## Security Considerations

### Production Security Checklist

- [ ] Use strong passwords and API keys
- [ ] Enable SSL/TLS encryption
- [ ] Configure firewall rules
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Backup encryption
- [ ] Network segmentation
- [ ] Rate limiting configuration
- [ ] Input validation and sanitization
- [ ] Regular security audits

### Network Security

```bash
# Configure firewall
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8501/tcp   # Block direct app access
```

### Data Protection

- Encrypt sensitive data at rest
- Use secure communication protocols
- Implement proper access controls
- Regular backup verification
- Data retention policies
- GDPR/privacy compliance

This deployment guide provides comprehensive instructions for setting up the RAG system in various environments. Follow the appropriate section based on your deployment needs and environment requirements.