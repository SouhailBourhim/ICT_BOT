# Docker Desktop Visual Guide for RAG System

## 🎯 Quick Reference

### What to Look For in Docker Desktop

#### **Images Tab** 🖼️
```
Repository    Tag      Size     Created
rag-system    latest   2.1GB    2 minutes ago
python        3.10     1.2GB    1 hour ago
ollama/ollama latest   4.5GB    1 hour ago
```

#### **Containers Tab** 📦
```
Name                Status    Image              Ports
rag-system-app      Running   rag-system:latest  8501:8501
rag-system-ollama   Running   ollama/ollama      11434:11434
rag-system-nginx    Running   nginx:alpine       80:80, 443:443
rag-system-grafana  Running   grafana/grafana    3000:3000
rag-system-prometheus Running prom/prometheus    9090:9090
```

#### **Volumes Tab** 💾
```
Name           Driver   Size
rag_data       local    150MB
rag_cache      local    500MB
rag_logs       local    10MB
ollama_data    local    4.2GB
```

## 🚀 Common Tasks

### **1. Start the RAG System**
**Method 1: Using Scripts**
```bash
./start-docker.sh
# Choose option 1 or 2
```

**Method 2: Docker Desktop GUI**
1. Go to **Containers** tab
2. Find containers starting with `rag-system-`
3. Click **Play** ▶️ button for each

**Method 3: Docker Compose**
```bash
cd deployment/docker
docker-compose up -d
```

### **2. Access Your Application**
Once containers are running:

| Service | URL | Purpose |
|---------|-----|---------|
| **RAG System** | http://localhost:8501 | Main app |
| **Grafana** | http://localhost:3000 | Monitoring |
| **Prometheus** | http://localhost:9090 | Metrics |

**In Docker Desktop:**
- Go to **Containers** tab
- Click on port numbers to open in browser

### **3. View Application Logs**
**Docker Desktop:**
1. Click on `rag-system-app` container
2. Go to **Logs** tab
3. See real-time logs

**Command Line:**
```bash
docker logs rag-system-app -f
```

### **4. Stop the System**
**Docker Desktop:**
1. Go to **Containers** tab
2. Select all `rag-system-*` containers
3. Click **Stop** ⏹️

**Command Line:**
```bash
cd deployment/docker
docker-compose down
```

### **5. Update the Application**
1. **Rebuild image:**
   ```bash
   ./build-docker.sh
   ```

2. **Restart containers:**
   ```bash
   cd deployment/docker
   docker-compose up -d --force-recreate
   ```

## 🔧 Troubleshooting in Docker Desktop

### **Container Won't Start**
1. Click on container name
2. Check **Logs** tab for errors
3. Look for port conflicts or missing dependencies

### **High Resource Usage**
1. Go to **Containers** tab
2. Check CPU/Memory columns
3. Consider stopping unused containers

### **Storage Issues**
1. Go to **Images** tab
2. Remove unused images (click trash icon)
3. Go to **Volumes** tab
4. Clean up unused volumes

### **Network Issues**
1. Go to **Networks** tab
2. Check if `rag-network` exists
3. Restart containers if needed

## 📊 Monitoring Your System

### **Container Health**
In **Containers** tab, look for:
- 🟢 **Green dot:** Healthy/Running
- 🔴 **Red dot:** Stopped/Error
- 🟡 **Yellow dot:** Starting/Unhealthy

### **Resource Usage**
Monitor in real-time:
- **CPU %:** Should be < 50% normally
- **Memory:** Should be < 2GB per container
- **Network I/O:** Shows activity

### **Logs to Watch**
Key log messages to look for:
```
✅ Good:
- "Streamlit server started"
- "Health check passed"
- "Database connected"

❌ Problems:
- "Connection refused"
- "Out of memory"
- "Port already in use"
```

## 🎛️ Advanced Features

### **Container Shell Access**
1. Click on container name
2. Go to **Exec** tab
3. Run: `/bin/bash` or `/bin/sh`
4. Execute commands inside container

### **File Browser**
1. Click on container name
2. Go to **Files** tab
3. Browse container filesystem
4. View/edit files directly

### **Environment Variables**
1. Click on container name
2. Go to **Inspect** tab
3. See all environment variables
4. Check configuration

## 🔗 Quick Links

### **Application URLs**
- **Main App:** [http://localhost:8501](http://localhost:8501)
- **Grafana:** [http://localhost:3000](http://localhost:3000) (admin/admin123)
- **Prometheus:** [http://localhost:9090](http://localhost:9090)

### **Useful Commands**
```bash
# Check status
./health-check.sh

# View logs
docker-compose logs -f

# Restart everything
docker-compose restart

# Clean up
docker system prune -f
```

## 💡 Pro Tips

1. **Bookmark URLs:** Save the application URLs in your browser
2. **Monitor Resources:** Keep an eye on CPU/Memory usage
3. **Regular Cleanup:** Remove unused images/containers weekly
4. **Backup Data:** Export volumes before major updates
5. **Use Health Checks:** Run `./health-check.sh` regularly

## 🆘 Need Help?

If you can't find your containers:
1. Check if Docker Desktop is running
2. Run: `docker ps -a` in terminal
3. Look for containers with `rag-system` in the name
4. Use the troubleshooting script: `./docker-troubleshoot.sh`