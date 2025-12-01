#!/usr/bin/env python3
"""
Import ingestion data from another machine.
This script unpacks and installs the processed vector database and metadata.
"""

import os
import shutil
import tarfile
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import logging
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_ingestion_data(archive_path, target_chroma="chroma", target_data="data", backup=True):
    """Import ingestion data from a transfer package."""
    
    archive_path = Path(archive_path)
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")
    
    logger.info(f"Importing ingestion data from: {archive_path}")
    
    # Create backup if requested
    if backup:
        backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Backup existing ChromaDB
        chroma_path = Path(target_chroma)
        if chroma_path.exists():
            backup_chroma = Path(f"backup/chroma_backup_{backup_timestamp}")
            backup_chroma.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(chroma_path, backup_chroma)
            logger.info(f"Backed up existing ChromaDB to {backup_chroma}")
        
        # Backup existing data
        data_path = Path(target_data)
        if data_path.exists():
            backup_data = Path(f"backup/data_backup_{backup_timestamp}")
            backup_data.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(data_path, backup_data)
            logger.info(f"Backed up existing data to {backup_data}")
    
    # Extract archive
    temp_dir = Path("temp_import")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        logger.info("Extracting archive...")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(temp_dir)
        
        # Find the extracted directory
        extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
        if not extracted_dirs:
            raise ValueError("No directories found in archive")
        
        package_dir = extracted_dirs[0]
        logger.info(f"Extracted to: {package_dir}")
        
        # Read metadata
        metadata_file = package_dir / "export_metadata.json"
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
            logger.info(f"Package created: {metadata.get('export_date')}")
            logger.info(f"Contents: {metadata.get('contents')}")
            
            if 'statistics' in metadata:
                stats = metadata['statistics']
                logger.info(f"Documents: {stats.get('document_count')}, Chunks: {stats.get('chunk_count')}")
        
        # Import ChromaDB
        source_chroma = package_dir / "chroma"
        if source_chroma.exists():
            target_chroma_path = Path(target_chroma)
            
            # Remove existing ChromaDB
            if target_chroma_path.exists():
                shutil.rmtree(target_chroma_path)
            
            # Copy new ChromaDB
            shutil.copytree(source_chroma, target_chroma_path)
            logger.info(f"ChromaDB imported to {target_chroma_path}")
        else:
            logger.warning("No ChromaDB found in package")
        
        # Import data files
        source_data = package_dir / "data"
        if source_data.exists():
            target_data_path = Path(target_data)
            target_data_path.mkdir(parents=True, exist_ok=True)
            
            # Copy database files
            for db_file in ["metadata.db", "conversations.db", "analytics.db"]:
                source_db = source_data / db_file
                if source_db.exists():
                    target_db = target_data_path / db_file
                    shutil.copy2(source_db, target_db)
                    logger.info(f"Imported {db_file}")
            
            # Copy vocabulary files
            source_vocab = source_data / "vocabulary"
            if source_vocab.exists():
                target_vocab = target_data_path / "vocabulary"
                if target_vocab.exists():
                    shutil.rmtree(target_vocab)
                shutil.copytree(source_vocab, target_vocab)
                logger.info("Imported vocabulary files")
        
        # Verify import
        logger.info("Verifying import...")
        verification_results = verify_import(target_chroma, target_data)
        
        if verification_results['success']:
            logger.info("Import verification successful!")
            for key, value in verification_results.items():
                if key != 'success':
                    logger.info(f"  {key}: {value}")
        else:
            logger.warning("Import verification failed!")
            for key, value in verification_results.items():
                if key != 'success':
                    logger.warning(f"  {key}: {value}")
        
        logger.info("Import completed successfully!")
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise
    
    finally:
        # Clean up temporary directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def verify_import(chroma_dir, data_dir):
    """Verify the imported data."""
    results = {'success': True}
    
    try:
        # Check ChromaDB
        chroma_path = Path(chroma_dir)
        if chroma_path.exists():
            results['chroma_db'] = 'Present'
            # Count files in ChromaDB
            chroma_files = list(chroma_path.rglob('*'))
            results['chroma_files'] = len([f for f in chroma_files if f.is_file()])
        else:
            results['chroma_db'] = 'Missing'
            results['success'] = False
        
        # Check metadata database
        metadata_db = Path(data_dir) / "metadata.db"
        if metadata_db.exists():
            conn = sqlite3.connect(metadata_db)
            cursor = conn.cursor()
            
            # Check documents table
            try:
                cursor.execute("SELECT COUNT(*) FROM documents")
                doc_count = cursor.fetchone()[0]
                results['documents'] = doc_count
            except sqlite3.OperationalError:
                results['documents'] = 'Table not found'
                results['success'] = False
            
            # Check chunks table
            try:
                cursor.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cursor.fetchone()[0]
                results['chunks'] = chunk_count
            except sqlite3.OperationalError:
                results['chunks'] = 'Table not found'
                results['success'] = False
            
            conn.close()
        else:
            results['metadata_db'] = 'Missing'
            results['success'] = False
        
        # Check vocabulary files
        vocab_dir = Path(data_dir) / "vocabulary"
        if vocab_dir.exists():
            vocab_files = list(vocab_dir.glob('*.json'))
            results['vocabulary_files'] = len(vocab_files)
        else:
            results['vocabulary_files'] = 0
        
    except Exception as e:
        results['verification_error'] = str(e)
        results['success'] = False
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import RAG ingestion data")
    parser.add_argument("archive", help="Path to the ingestion data archive (.tar.gz)")
    parser.add_argument("--chroma-dir", default="chroma", help="Target ChromaDB directory")
    parser.add_argument("--data-dir", default="data", help="Target data directory")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup of existing data")
    
    args = parser.parse_args()
    
    try:
        import_ingestion_data(
            args.archive, 
            args.chroma_dir, 
            args.data_dir, 
            backup=not args.no_backup
        )
        print("SUCCESS: Ingestion data imported successfully!")
        print("\nNext steps:")
        print("1. Test the system: python -c \"from src.core.system import RAGSystem; system = RAGSystem(); system.initialize(); print('Status:', system.health_check().get('overall_status'))\"")
        print("2. Start the application: streamlit run src/app.py")
        
    except Exception as e:
        print(f"ERROR: Import failed - {e}")
        exit(1)