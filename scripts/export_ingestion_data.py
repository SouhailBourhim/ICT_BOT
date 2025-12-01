#!/usr/bin/env python3
"""
Export ingestion data for transfer to another machine.
This script packages the processed vector database and metadata for transfer.
"""

import os
import shutil
import tarfile
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def export_ingestion_data(export_dir="/app/export", source_chroma="/app/chroma", source_data="/app/data"):
    """Export all ingestion data to a transferable package."""
    
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"rag_ingestion_data_{timestamp}"
    package_dir = export_path / package_name
    
    logger.info(f"Creating export package: {package_name}")
    
    try:
        # Create package directory
        package_dir.mkdir(exist_ok=True)
        
        # Export ChromaDB
        chroma_source = Path(source_chroma)
        if chroma_source.exists():
            chroma_dest = package_dir / "chroma"
            logger.info("Exporting ChromaDB...")
            shutil.copytree(chroma_source, chroma_dest)
            logger.info(f"ChromaDB exported to {chroma_dest}")
        else:
            logger.warning(f"ChromaDB not found at {chroma_source}")
        
        # Export metadata databases
        data_source = Path(source_data)
        if data_source.exists():
            data_dest = package_dir / "data"
            data_dest.mkdir(exist_ok=True)
            
            # Copy database files
            for db_file in ["metadata.db", "conversations.db", "analytics.db"]:
                db_path = data_source / db_file
                if db_path.exists():
                    shutil.copy2(db_path, data_dest / db_file)
                    logger.info(f"Exported {db_file}")
            
            # Copy vocabulary files if they exist
            vocab_source = data_source / "vocabulary"
            if vocab_source.exists():
                vocab_dest = data_dest / "vocabulary"
                shutil.copytree(vocab_source, vocab_dest)
                logger.info("Exported vocabulary files")
        
        # Create export metadata
        metadata = {
            "export_timestamp": timestamp,
            "export_date": datetime.now().isoformat(),
            "package_name": package_name,
            "contents": {
                "chroma_db": (package_dir / "chroma").exists(),
                "metadata_db": (package_dir / "data" / "metadata.db").exists(),
                "conversations_db": (package_dir / "data" / "conversations.db").exists(),
                "analytics_db": (package_dir / "data" / "analytics.db").exists(),
                "vocabulary": (package_dir / "data" / "vocabulary").exists()
            }
        }
        
        # Add database statistics
        try:
            metadata_db_path = package_dir / "data" / "metadata.db"
            if metadata_db_path.exists():
                conn = sqlite3.connect(metadata_db_path)
                cursor = conn.cursor()
                
                # Get document count
                cursor.execute("SELECT COUNT(*) FROM documents")
                doc_count = cursor.fetchone()[0]
                
                # Get chunk count
                cursor.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cursor.fetchone()[0]
                
                metadata["statistics"] = {
                    "document_count": doc_count,
                    "chunk_count": chunk_count
                }
                
                conn.close()
                logger.info(f"Processed {doc_count} documents, {chunk_count} chunks")
        except Exception as e:
            logger.warning(f"Could not extract statistics: {e}")
        
        # Save metadata
        with open(package_dir / "export_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Create compressed archive
        archive_path = export_path / f"{package_name}.tar.gz"
        logger.info(f"Creating compressed archive: {archive_path}")
        
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(package_dir, arcname=package_name)
        
        # Calculate archive size
        archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
        logger.info(f"Archive created: {archive_path} ({archive_size_mb:.1f} MB)")
        
        # Create transfer instructions
        instructions = f"""
# RAG System Ingestion Data Transfer Instructions

## Package Information
- Package: {package_name}.tar.gz
- Created: {datetime.now().isoformat()}
- Size: {archive_size_mb:.1f} MB
- Contents: {metadata['contents']}

## Transfer Steps

### 1. Download the package from the ingestion machine:
```bash
# Copy from Docker container
docker cp rag-data-exporter:/app/export/{package_name}.tar.gz .

# Or download from shared volume
cp /path/to/docker/volumes/ingestion_output/_data/{package_name}.tar.gz .
```

### 2. Transfer to your local machine:
```bash
# Using scp
scp {package_name}.tar.gz user@your-local-machine:/path/to/rag-system/

# Or use any file transfer method (USB, cloud storage, etc.)
```

### 3. Import on your local machine:
```bash
# Navigate to your RAG system directory
cd /path/to/your/rag-system

# Run the import script
python scripts/import_ingestion_data.py {package_name}.tar.gz
```

## Verification
After import, verify the data:
```bash
python -c "
from src.core.system import RAGSystem
system = RAGSystem()
system.initialize()
health = system.health_check()
print('System status:', health.get('overall_status'))
"
```

## Statistics
- Documents processed: {metadata.get('statistics', {}).get('document_count', 'Unknown')}
- Chunks created: {metadata.get('statistics', {}).get('chunk_count', 'Unknown')}
"""
        
        with open(export_path / f"{package_name}_instructions.txt", "w") as f:
            f.write(instructions)
        
        # Clean up temporary directory
        shutil.rmtree(package_dir)
        
        logger.info("Export completed successfully!")
        logger.info(f"Transfer package: {archive_path}")
        logger.info(f"Instructions: {export_path / f'{package_name}_instructions.txt'}")
        
        return str(archive_path)
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        # Clean up on failure
        if package_dir.exists():
            shutil.rmtree(package_dir)
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export RAG ingestion data")
    parser.add_argument("--export-dir", default="/app/export", help="Export directory")
    parser.add_argument("--chroma-dir", default="/app/chroma", help="ChromaDB directory")
    parser.add_argument("--data-dir", default="/app/data", help="Data directory")
    
    args = parser.parse_args()
    
    try:
        archive_path = export_ingestion_data(args.export_dir, args.chroma_dir, args.data_dir)
        print(f"SUCCESS: Export package created at {archive_path}")
    except Exception as e:
        print(f"ERROR: Export failed - {e}")
        exit(1)