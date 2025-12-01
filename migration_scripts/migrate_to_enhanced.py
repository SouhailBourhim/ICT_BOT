#!/usr/bin/env python3
"""
Migration script to upgrade existing RAG system data to enhanced schema.
"""
import os
import sys
import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import get_settings
from processors.metadata_extractor import MetadataExtractor
from processors.semantic_chunker import SemanticChunker
from managers.conversation_manager import ConversationManager


class DataMigrator:
    """Handles migration from legacy to enhanced schema."""
    
    def __init__(self):
        """Initialize the migrator."""
        self.config = get_settings()
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for migration."""
        logger = logging.getLogger("migration")
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def run_migration(self, backup: bool = True) -> bool:
        """Run the complete migration process."""
        try:
            self.logger.info("Starting migration to enhanced schema...")
            
            if backup:
                self._create_backup()
            
            # Migration steps
            self._migrate_vector_database()
            self._migrate_metadata_schema()
            self._initialize_conversation_database()
            self._initialize_analytics_database()
            self._update_configuration()
            
            self.logger.info("Migration completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            if backup:
                self._restore_backup()
            return False
    
    def _create_backup(self):
        """Create backup of existing data."""
        self.logger.info("Creating backup of existing data...")
        
        backup_dir = Path("backup") / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup vector database
        chroma_path = Path(self.config.database.chroma_path)
        if chroma_path.exists():
            shutil.copytree(chroma_path, backup_dir / "chroma")
            self.logger.info(f"Vector database backed up to {backup_dir / 'chroma'}")
        
        # Backup any existing metadata
        metadata_path = Path(self.config.database.metadata_db_path)
        if metadata_path.exists():
            shutil.copy2(metadata_path, backup_dir / "metadata.db")
            self.logger.info(f"Metadata database backed up to {backup_dir / 'metadata.db'}")
        
        # Store backup location
        self.backup_dir = backup_dir
    
    def _restore_backup(self):
        """Restore from backup if migration fails."""
        if hasattr(self, 'backup_dir') and self.backup_dir.exists():
            self.logger.info("Restoring from backup...")
            
            # Restore vector database
            chroma_backup = self.backup_dir / "chroma"
            if chroma_backup.exists():
                chroma_path = Path(self.config.database.chroma_path)
                if chroma_path.exists():
                    shutil.rmtree(chroma_path)
                shutil.copytree(chroma_backup, chroma_path)
            
            # Restore metadata database
            metadata_backup = self.backup_dir / "metadata.db"
            if metadata_backup.exists():
                shutil.copy2(metadata_backup, self.config.database.metadata_db_path)
            
            self.logger.info("Backup restored successfully")
    
    def _migrate_vector_database(self):
        """Migrate vector database to enhanced format."""
        self.logger.info("Migrating vector database...")
        
        # The vector database structure remains compatible
        # We'll enhance it by re-processing documents with better metadata
        chroma_path = Path(self.config.database.chroma_path)
        
        if not chroma_path.exists():
            self.logger.warning("No existing vector database found. Skipping migration.")
            return
        
        # Check if migration is needed by looking for enhanced metadata
        try:
            from langchain_chroma import Chroma
            from langchain_ollama import OllamaEmbeddings
            
            embeddings = OllamaEmbeddings(model=self.config.model.ollama_model)
            db = Chroma(persist_directory=str(chroma_path), embedding_function=embeddings)
            
            # Sample a few documents to check metadata structure
            sample_docs = db.get(limit=5)
            
            if sample_docs['documents']:
                # Check if enhanced metadata exists
                sample_metadata = sample_docs.get('metadatas', [{}])[0]
                
                if not self._has_enhanced_metadata(sample_metadata):
                    self.logger.info("Vector database needs metadata enhancement")
                    self._enhance_vector_metadata(db)
                else:
                    self.logger.info("Vector database already has enhanced metadata")
            
        except Exception as e:
            self.logger.warning(f"Could not check vector database: {e}")
    
    def _has_enhanced_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Check if metadata has enhanced fields."""
        enhanced_fields = [
            'content_type', 'hierarchical_context', 'document_structure',
            'processing_version', 'chunk_position'
        ]
        return any(field in metadata for field in enhanced_fields)
    
    def _enhance_vector_metadata(self, db):
        """Enhance existing vector database with better metadata."""
        self.logger.info("Enhancing vector database metadata...")
        
        # This would require re-processing documents
        # For now, we'll mark the database as needing re-ingestion
        marker_file = Path(self.config.database.chroma_path) / ".needs_reingestion"
        marker_file.touch()
        
        with open(marker_file, 'w') as f:
            json.dump({
                "migration_date": datetime.now().isoformat(),
                "reason": "Enhanced metadata migration",
                "action_required": "Re-run document ingestion with enhanced pipeline"
            }, f, indent=2)
        
        self.logger.info("Vector database marked for re-ingestion with enhanced metadata")
    
    def _migrate_metadata_schema(self):
        """Create or migrate metadata database schema."""
        self.logger.info("Setting up enhanced metadata database...")
        
        metadata_db_path = Path(self.config.database.metadata_db_path)
        metadata_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(metadata_db_path))
        cursor = conn.cursor()
        
        # Create enhanced metadata tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                course_module TEXT,
                language TEXT DEFAULT 'fr',
                page_count INTEGER,
                word_count INTEGER,
                creation_date TIMESTAMP,
                ingestion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processing_version TEXT DEFAULT '2.0',
                metadata_json TEXT,
                UNIQUE(file_path)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT DEFAULT 'text',
                chunk_index INTEGER NOT NULL,
                page_number INTEGER,
                hierarchical_context TEXT,
                position_in_document REAL,
                token_count INTEGER,
                embedding_model TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                processing_stage TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                processing_time_seconds REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks (document_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_content_type ON chunks (content_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_course_module ON documents (course_module)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_processing_logs_document_id ON processing_logs (document_id)")
        
        conn.commit()
        conn.close()
        
        self.logger.info("Enhanced metadata database schema created")
    
    def _initialize_conversation_database(self):
        """Initialize conversation management database."""
        self.logger.info("Setting up conversation database...")
        
        try:
            conversation_manager = ConversationManager()
            # This will create the database schema if it doesn't exist
            self.logger.info("Conversation database initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize conversation database: {e}")
    
    def _initialize_analytics_database(self):
        """Initialize analytics database."""
        self.logger.info("Setting up analytics database...")
        
        analytics_db_path = Path(self.config.database.analytics_db_path)
        analytics_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(analytics_db_path))
        cursor = conn.cursor()
        
        # Create analytics tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                query TEXT NOT NULL,
                query_type TEXT,
                response_time_ms INTEGER,
                retrieval_count INTEGER,
                confidence_score REAL,
                user_feedback INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                context_json TEXT,
                stack_trace TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_analytics_timestamp ON query_analytics (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics (metric_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_type ON error_logs (error_type)")
        
        conn.commit()
        conn.close()
        
        self.logger.info("Analytics database initialized")
    
    def _update_configuration(self):
        """Update configuration for enhanced features."""
        self.logger.info("Updating configuration...")
        
        # Create enhanced configuration file
        config_updates = {
            "migration_completed": True,
            "migration_date": datetime.now().isoformat(),
            "enhanced_features_enabled": True,
            "processing_version": "2.0"
        }
        
        config_file = Path("reports/migration_status.json")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config_updates, f, indent=2)
        
        self.logger.info("Configuration updated")
    
    def verify_migration(self) -> bool:
        """Verify that migration was successful."""
        self.logger.info("Verifying migration...")
        
        try:
            # Check database files exist
            required_dbs = [
                self.config.database.metadata_db_path,
                self.config.database.conversation_db_path,
                self.config.database.analytics_db_path
            ]
            
            for db_path in required_dbs:
                if not Path(db_path).exists():
                    self.logger.error(f"Required database not found: {db_path}")
                    return False
            
            # Check configuration
            config_file = Path("reports/migration_status.json")
            if not config_file.exists():
                self.logger.error("Migration status file not found")
                return False
            
            self.logger.info("Migration verification passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Migration verification failed: {e}")
            return False


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate RAG system to enhanced schema")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    parser.add_argument("--verify-only", action="store_true", help="Only verify migration")
    
    args = parser.parse_args()
    
    migrator = DataMigrator()
    
    if args.verify_only:
        success = migrator.verify_migration()
        sys.exit(0 if success else 1)
    
    success = migrator.run_migration(backup=not args.no_backup)
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("You can now use the enhanced RAG system features.")
        print("\n📝 Next steps:")
        print("1. Re-run document ingestion to get enhanced metadata")
        print("2. Test the enhanced features in the web interface")
        print("3. Check the migration logs for any warnings")
    else:
        print("\n❌ Migration failed!")
        print("Check the logs for details and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()