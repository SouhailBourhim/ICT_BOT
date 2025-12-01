# Docker-Based Document Ingestion Guide

This guide explains how to perform document ingestion on a high-memory machine using Docker and transfer the results to your local system.

## Overview

The Docker ingestion setup allows you to:
1. Run document processing on a machine with sufficient RAM
2. Export the processed vector database and metadata
3. Import the results to your local system
4. Continue using the RAG system locally

## Prerequisites

### High-Memory Machine (Ingestion Server)
- Docker and Docker Compose installed
- 16GB+ RAM recommended (minimum 8GB)
- Sufficient disk space for documents and processed data
- Internet connection for downloading models

### Local Machine
- Your existing RAG system setup
- Python environment with required packages
- Sufficient disk space for imported data

## Step-by-Step Process

### Phase 1: Setup on High-Memory Machine

#### 1. Prepare the Ingestion Environment

```bash
# Clone or copy your RAG system to the high-memory machine
git clone <your-repo> rag-ingestion
cd rag-ingestion

# Create documents directory
mkdir -p deployment/docker/documents

# Copy your documents to the documents directory
cp /path/to/your/documents/* deployment/docker/documents/
```

#### 2. Configure Ingestion Settings

The ingestion setup uses optimized settings for memory efficiency:

```bash
# Review ingestion configuration
cat deployment/docker/ingestion.env

# Key optimizations:
# - BATCH_SIZE=3 (smaller batches)
# - MAX_CHUNK_SIZE=1500 (smaller chunks)
# - ENABLE_CACHING=false (no caching during ingestion)
# - MAX_CONCURRENT_REQUESTS=2 (limited concurrency)
```

#### 3. Start the Ingestion Process

```bash
# Navigate to Docker directory
cd deployment/docker

# Start Ollama service first
docker-compose -f docker-compose.ingestion.yml up -d ollama-ingestion

# Wait for Ollama to be ready (check logs)
docker-compose -f docker-compose.ingestion.yml logs -f ollama-ingestion

# Download the required model
docker exec rag-ingestion-ollama ollama pull llama3

# Start the ingestion process
docker-compose -f docker-compose.ingestion.yml up rag-ingestion
```

#### 4. Monitor Ingestion Progress

```bash
# Watch ingestion logs
docker-compose -f docker-compose.ingestion.yml logs -f rag-ingestion

# Check resource usage
docker stats rag-ingestion-processor

# Monitor disk usage
docker exec rag-ingestion-processor du -sh /app/chroma /app/data
```

### Phase 2: Export Processed Data

#### 1. Export the Data

```bash
# Run the data export service
docker-compose -f docker-compose.ingestion.yml --profile export up data-exporter

# Or run export manually
docker exec rag-ingestion-processor python scripts/export_ingestion_data.py
```

#### 2. Retrieve the Export Package

```bash
# Copy the export package from the container
docker cp rag-data-exporter:/app/export/ ./export/

# List available packages
ls -la export/

# You should see files like:
# - rag_ingestion_data_YYYYMMDD_HHMMSS.tar.gz
# - rag_ingestion_data_YYYYMMDD_HHMMSS_instructions.txt
```

### Phase 3: Transfer to Local Machine

#### 1. Transfer Methods

Choose the method that works best for your setup:

**Option A: Direct Network Transfer**
```bash
# Using scp
scp export/rag_ingestion_data_*.tar.gz user@local-machine:/path/to/rag-system/

# Using rsync
rsync -avz export/ user@local-machine:/path/to/rag-system/import/
```

**Option B: Cloud Storage**
```bash
# Upload to cloud storage
aws s3 cp export/rag_ingestion_data_*.tar.gz s3://your-bucket/
# Then download on local machine
aws s3 cp s3://your-bucket/rag_ingestion_data_*.tar.gz .
```

**Option C: USB/External Drive**
```bash
# Copy to external drive
cp export/rag_ingestion_data_*.tar.gz /media/usb-drive/
# Then copy from drive on local machine
```

### Phase 4: Import on Local Machine

#### 1. Import the Data

```bash
# Navigate to your local RAG system directory
cd /path/to/your/rag-system

# Import the data (this will backup existing data)
python scripts/import_ingestion_data.py rag_ingestion_data_YYYYMMDD_HHMMSS.tar.gz

# Or specify custom directories
python scripts/import_ingestion_data.py \
    --chroma-dir ./chroma \
    --data-dir ./data \
    rag_ingestion_data_YYYYMMDD_HHMMSS.tar.gz
```

#### 2. Verify the Import

```bash
# Test system initialization
python -c "
from src.core.system import RAGSystem
system = RAGSystem()
system.initialize()
health = system.health_check()
print('System status:', health.get('overall_status'))
print('Components:', list(health.keys()))
"

# Check database contents
python -c "
import sqlite3
conn = sqlite3.connect('data/metadata.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM documents')
doc_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM chunks')
chunk_count = cursor.fetchone()[0]
print(f'Documents: {doc_count}, Chunks: {chunk_count}')
conn.close()
"
```

#### 3. Start Your Local System

```bash
# Start the Streamlit application
streamlit run src/app.py

# Test with a query to verify everything works
```

## Advanced Configuration

### Memory Optimization

For very large document sets, you can further optimize memory usage:

```yaml
# In docker-compose.ingestion.yml, modify the rag-ingestion service:
environment:
  - BATCH_SIZE=1          # Process one document at a time
  - MAX_CHUNK_SIZE=1000   # Even smaller chunks
  - CHUNK_OVERLAP=100     # Smaller overlap
```

### Parallel Processing

For faster processing on multi-core machines:

```yaml
# Run multiple ingestion containers
services:
  rag-ingestion-1:
    # ... same config as rag-ingestion
    volumes:
      - ./documents/batch1:/app/data/documents:ro
  
  rag-ingestion-2:
    # ... same config as rag-ingestion
    volumes:
      - ./documents/batch2:/app/data/documents:ro
```

### Custom Document Processing

```bash
# Process specific document types
docker run --rm -v $(pwd)/documents:/app/data/documents \
  rag-ingestion python ingest_enhanced.py \
  --directory /app/data/documents \
  --file-types pdf,docx \
  --batch-size 2
```

## Troubleshooting

### Common Issues

#### 1. Out of Memory Errors
```bash
# Reduce batch size
docker-compose -f docker-compose.ingestion.yml down
# Edit ingestion.env: BATCH_SIZE=1
docker-compose -f docker-compose.ingestion.yml up rag-ingestion
```

#### 2. Ollama Model Download Fails
```bash
# Manually download model
docker exec rag-ingestion-ollama ollama pull llama3

# Check available models
docker exec rag-ingestion-ollama ollama list
```

#### 3. Disk Space Issues
```bash
# Check disk usage
docker system df
docker volume ls

# Clean up if needed
docker system prune -a
```

#### 4. Import Verification Fails
```bash
# Check import logs
python scripts/import_ingestion_data.py --help

# Manual verification
ls -la chroma/ data/
sqlite3 data/metadata.db ".tables"
```

### Performance Monitoring

```bash
# Monitor resource usage during ingestion
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check ingestion progress
docker exec rag-ingestion-processor tail -f /app/logs/ingestion.log

# Monitor Ollama performance
docker exec rag-ingestion-ollama curl -s http://localhost:11434/api/ps
```

## Cleanup

### On Ingestion Machine

```bash
# Stop and remove containers
docker-compose -f docker-compose.ingestion.yml down

# Remove volumes (optional - this deletes processed data)
docker volume rm $(docker volume ls -q | grep ingestion)

# Remove images (optional)
docker rmi $(docker images -q rag-ingestion*)
```

### On Local Machine

```bash
# Remove import archive after successful import
rm rag_ingestion_data_*.tar.gz

# Clean up backup files (optional)
rm -rf backup/chroma_backup_* backup/data_backup_*
```

## Best Practices

1. **Test with Small Dataset First**: Start with a few documents to verify the process
2. **Monitor Resources**: Keep an eye on memory and disk usage during ingestion
3. **Backup Before Import**: The import script creates backups, but verify they exist
4. **Verify After Import**: Always test the system after importing data
5. **Document Your Process**: Keep notes on settings that work for your document types
6. **Regular Exports**: If you frequently add documents, establish a regular export/import cycle

## Security Considerations

1. **Network Transfer**: Use secure methods (SSH, VPN) for transferring data
2. **Access Control**: Ensure only authorized users can access the ingestion machine
3. **Data Cleanup**: Securely delete temporary files and exports after transfer
4. **Container Security**: Keep Docker images updated and use non-root users

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs`
2. Verify system resources: `docker stats`
3. Test individual components: `docker exec -it container-name bash`
4. Review the troubleshooting section above
5. Check the main documentation for additional guidance