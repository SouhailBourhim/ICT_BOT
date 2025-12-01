# Docker Deployment Guide for RAG System

This guide explains how to build and deploy the RAG System using Docker containers.

## 🐳 Quick Start

### Option 1: Simple Docker Run

1. **Build the image:**

   ```bash
   ./build-docker.sh
   ```

2. **Run the container:**

   ```bash
   docker run -p 8501:8501 rag-system:latest
   ```

3. **Access the application:**
   Open http://localhost:8501 in your browser

### Option 2: Full Stack with Docker Compose

1. **Start all services:**

   ```bash
   cd deployment/docker
   docker-compose up -d
   ```

2. **Access services:**
   - RAG System: http://localhost:8501
   - Ollama API: http://localhost:11434
   - Grafana Dashboard: http://localhost:3000 (admin/admin123)
   - Prometheus: http://localhost:9090

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available
- 10GB free disk space

## 🏗️ Build Options

### Standard Build

```bash
./build-docker.sh
```

### Build with Custom Tag

```bash
./build-docker.sh v1.0.0
```

### Manual Build

```bash
docker build -f deployment/docker/Dockerfile -t rag-system:latest .
```

## 🚀 Deployment Options

### 1. Development Mode

```bash
# Single container for development
docker run -it --rm \
  -p 8501:8501 \
  -v $(pwd):/app \
  -e ENVIRONMENT=development \
  rag-system:latest
```

### 2. Production Mode with Docker Compose

```bash
cd deployment/docker
docker-compose up -d
```

### 3. Production Mode with External Ollama

```bash
docker run -d \
  --name rag-system \
  -p 8501:8501 \
  -e OLLAMA_BASE_URL=http://your-ollama-server:11434 \
  -e ENVIRONMENT=production \
  -v rag_data:/app/data \
  -v rag_cache:/app/cache \
  rag-system:latest
```

## 🔧 Configuration

### Environment Variables

| Variable                | Default                        | Description         |
| ----------------------- | ------------------------------ | ------------------- |
| `ENVIRONMENT`           | `development`                  | Environment mode    |
| `LOG_LEVEL`             | `INFO`                         | Logging level       |
| `OLLAMA_BASE_URL`       | `http://localhost:11434`       | Ollama API URL      |
| `DATABASE_URL`          | `sqlite:///data/rag_system.db` | Database connection |
| `CACHE_DIR`             | `/app/cache`                   | Cache directory     |
| `STREAMLIT_SERVER_PORT` | `8501`                         | Streamlit port      |

### Volume Mounts

| Volume       | Purpose                       |
| ------------ | ----------------------------- |
| `/app/data`  | Database and document storage |
| `/app/cache` | Vector embeddings cache       |
| `/app/logs`  | Application logs              |

## 📊 Monitoring

The Docker Compose setup includes monitoring with:

- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Health Checks**: Container health monitoring

### Health Check Endpoints

- RAG System: `http://localhost:8501/_stcore/health`
- Ollama: `http://localhost:11434/api/tags`

## 🛠️ Management Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f rag-system
```

### Scale Services

```bash
# Scale RAG system instances
docker-compose up -d --scale rag-system=3
```

### Update Services

```bash
# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d
```

### Backup Data

```bash
# Backup volumes
docker run --rm -v rag_data:/data -v $(pwd):/backup alpine tar czf /backup/rag_backup.tar.gz /data
```

### Restore Data

```bash
# Restore volumes
docker run --rm -v rag_data:/data -v $(pwd):/backup alpine tar xzf /backup/rag_backup.tar.gz -C /
```

## 🔒 Security Considerations

### Production Security

1. **Change default passwords** in docker-compose.yml
2. **Use SSL certificates** for HTTPS
3. **Configure firewall rules**
4. **Enable authentication** for monitoring services
5. **Use secrets management** for sensitive data

### SSL Configuration

Place SSL certificates in `deployment/docker/ssl/`:

- `cert.pem` - SSL certificate
- `key.pem` - Private key

## 🐛 Troubleshooting

### Common Issues

1. **Port conflicts:**

   ```bash
   # Check port usage
   netstat -tulpn | grep :8501

   # Use different port
   docker run -p 8502:8501 rag-system:latest
   ```

2. **Memory issues:**

   ```bash
   # Increase Docker memory limit
   # Docker Desktop: Settings > Resources > Memory

   # Check container memory usage
   docker stats rag-system
   ```

3. **Ollama connection issues:**

   ```bash
   # Check Ollama container
   docker-compose logs ollama

   # Test Ollama API
   curl http://localhost:11434/api/tags
   ```

4. **Permission issues:**
   ```bash
   # Fix volume permissions
   sudo chown -R 1000:1000 ./data ./cache ./logs
   ```

### Debug Mode

```bash
# Run with debug output
docker run -it --rm \
  -p 8501:8501 \
  -e LOG_LEVEL=DEBUG \
  rag-system:latest
```

## 📈 Performance Tuning

### Resource Limits

```yaml
# In docker-compose.yml
services:
  rag-system:
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
        reservations:
          cpus: "1.0"
          memory: 2G
```

### Optimization Tips

1. **Use SSD storage** for volumes
2. **Allocate sufficient RAM** (minimum 4GB)
3. **Enable GPU support** for Ollama if available
4. **Use Redis** for caching in production
5. **Configure load balancing** for multiple instances

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Deploy
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: ./build-docker.sh ${{ github.sha }}
      - name: Deploy to production
        run: |
          docker tag rag-system:${{ github.sha }} rag-system:latest
          docker-compose up -d
```

## 📞 Support

For issues and questions:

1. Check the logs: `docker-compose logs`
2. Review this documentation
3. Check the main README.md
4. Open an issue in the repository

## 🔗 Related Documentation

- [Enhanced Deployment Guide](docs/ENHANCED_DEPLOYMENT_GUIDE.md)
- [Admin Guide](docs/ADMIN_GUIDE.md)
- [User Guide](docs/USER_GUIDE.md)
