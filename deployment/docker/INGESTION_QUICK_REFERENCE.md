# Docker Ingestion Quick Reference

## 🚀 Quick Start Commands

### Setup (One-time)
```bash
# Run setup script
./scripts/setup_docker_ingestion.sh

# Copy documents
cp /path/to/documents/* deployment/docker/documents/
```

### Ingestion Process
```bash
cd deployment/docker

# 1. Start Ollama
docker-compose -f docker-compose.ingestion.yml up -d ollama-ingestion

# 2. Download model
docker exec rag-ingestion-ollama ollama pull llama3

# 3. Start ingestion
docker-compose -f docker-compose.ingestion.yml up rag-ingestion

# 4. Export data
docker-compose -f docker-compose.ingestion.yml --profile export up data-exporter
```

### Transfer & Import
```bash
# Copy export package
docker cp rag-data-exporter:/app/export/ ./

# Transfer to local machine (choose one method)
scp export/rag_ingestion_data_*.tar.gz user@local:/path/to/rag/
# OR use USB, cloud storage, etc.

# Import on local machine
python scripts/import_ingestion_data.py rag_ingestion_data_*.tar.gz
```

## 📊 Monitoring Commands

```bash
# Watch logs
docker-compose -f docker-compose.ingestion.yml logs -f rag-ingestion

# Check resources
docker stats rag-ingestion-processor

# Check progress
docker exec rag-ingestion-processor ls -la /app/chroma /app/data

# Check export status
docker exec rag-data-exporter ls -la /app/export
```

## ⚙️ Configuration Tweaks

### Low Memory (< 8GB RAM)
```bash
# Edit ingestion.env
BATCH_SIZE=1
MAX_CHUNK_SIZE=800
CHUNK_OVERLAP=80
```

### High Memory (16GB+ RAM)
```bash
# Edit ingestion.env
BATCH_SIZE=10
MAX_CHUNK_SIZE=2000
CHUNK_OVERLAP=200
```

### Specific File Types Only
```bash
# Custom ingestion command
docker run --rm \
  -v $(pwd)/documents:/app/data/documents:ro \
  -v ingestion_chroma:/app/chroma \
  -v ingestion_data:/app/data \
  rag-ingestion \
  python ingest_enhanced.py --file-types pdf,docx
```

## 🔧 Troubleshooting

### Out of Memory
```bash
# Reduce batch size
docker-compose -f docker-compose.ingestion.yml down
# Edit ingestion.env: BATCH_SIZE=1
docker-compose -f docker-compose.ingestion.yml up rag-ingestion
```

### Model Download Issues
```bash
# Manual model download
docker exec rag-ingestion-ollama ollama pull llama3
docker exec rag-ingestion-ollama ollama list
```

### Check Disk Space
```bash
docker system df
du -sh deployment/docker/documents
```

### Restart Process
```bash
# Clean restart
docker-compose -f docker-compose.ingestion.yml down
docker volume rm ingestion_chroma ingestion_data
docker-compose -f docker-compose.ingestion.yml up -d ollama-ingestion
# Wait, then continue with step 2 above
```

## 📁 File Locations

| Component | Container Path | Host Path |
|-----------|---------------|-----------|
| Documents | `/app/data/documents` | `./documents/` |
| ChromaDB | `/app/chroma` | Docker volume |
| Metadata | `/app/data` | Docker volume |
| Exports | `/app/export` | Docker volume |
| Logs | `/app/logs` | Docker volume |

## 🎯 Success Indicators

✅ **Ingestion Complete**: Container exits with code 0  
✅ **Export Ready**: Files in `/app/export/` directory  
✅ **Import Success**: Verification shows documents and chunks  
✅ **System Ready**: Health check returns "healthy"  

## 📞 Getting Help

1. Check logs: `docker-compose logs rag-ingestion`
2. Verify setup: `./scripts/setup_docker_ingestion.sh`
3. Read full guide: `docs/deployment/DOCKER_INGESTION_GUIDE.md`
4. Test locally first with small document set