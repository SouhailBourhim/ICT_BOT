"""
Enhanced document ingestion pipeline with semantic chunking and metadata storage.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import os
import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
import chromadb
from src.models.base import ProcessedChunk, DocumentMetadata
from .document_processor import DocumentProcessor, BatchProcessor


class IngestionPipeline:
    """
    Enhanced ingestion pipeline for processing and storing documents.
    
    Features:
    - Semantic chunking with hierarchical context
    - Comprehensive metadata extraction and storage
    - Progress tracking and error handling
    - Batch processing for large document sets
    - Enhanced database schema for metadata
    """
    
    def __init__(self, 
                 data_path: str = "data",
                 chroma_path: str = "chroma",
                 metadata_db_path: str = "metadata.db",
                 embedding_model: str = "llama3"):
        """
        Initialize the ingestion pipeline.
        
        Args:
            data_path: Path to the data directory
            chroma_path: Path to the ChromaDB directory
            metadata_db_path: Path to the metadata SQLite database
            embedding_model: Name of the embedding model to use
        """
        self.data_path = data_path
        self.chroma_path = chroma_path
        self.metadata_db_path = metadata_db_path
        self.embedding_model = embedding_model
        
        # Initialize components
        self.document_processor = DocumentProcessor()
        self.batch_processor = BatchProcessor(self.document_processor)
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize databases
        self._initialize_metadata_db()
    
    def ingest_documents(self, 
                        file_paths: Optional[List[str]] = None,
                        show_progress: bool = True,
                        clear_existing: bool = False) -> Dict[str, Any]:
        """
        Ingest documents into the system.
        
        Args:
            file_paths: Optional list of specific file paths to process
            show_progress: Whether to show progress information
            clear_existing: Whether to clear existing data before ingestion
            
        Returns:
            Dictionary with ingestion results and statistics
        """
        start_time = datetime.now()
        
        if clear_existing:
            self._clear_existing_data()
        
        # Determine files to process
        if file_paths is None:
            file_paths = self._discover_files()
        
        if not file_paths:
            self.logger.warning("No files found to process")
            return {
                'status': 'completed',
                'files_processed': 0,
                'chunks_created': 0,
                'errors': [],
                'duration': 0
            }
        
        self.logger.info(f"Starting ingestion of {len(file_paths)} files")
        
        # Process documents
        progress_callback = self.batch_processor.create_progress_tracker(show_progress)
        results = self.batch_processor.process_directory(
            self.data_path, 
            progress_callback=progress_callback
        ) if file_paths is None else self.document_processor.process_batch(
            file_paths, 
            progress_callback
        )
        
        # Store results
        ingestion_stats = self._store_results(results)
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        
        # Compile final results
        final_results = {
            'status': 'completed',
            'files_processed': ingestion_stats['files_processed'],
            'chunks_created': ingestion_stats['chunks_created'],
            'errors': ingestion_stats['errors'],
            'duration': duration,
            'files_with_errors': ingestion_stats['files_with_errors'],
            'total_documents': len(file_paths)
        }
        
        self.logger.info(f"Ingestion completed: {final_results}")
        return final_results
    
    def ingest_single_document(self, file_path: str) -> Dict[str, Any]:
        """
        Ingest a single document.
        
        Args:
            file_path: Path to the document to ingest
            
        Returns:
            Dictionary with ingestion results
        """
        try:
            # Process document
            chunks = self.document_processor.process_document(file_path)
            
            if not chunks:
                return {
                    'status': 'no_content',
                    'file_path': file_path,
                    'chunks_created': 0,
                    'error': 'No content extracted'
                }
            
            # Store document metadata
            document_metadata = chunks[0].metadata.get('document_metadata')
            if document_metadata:
                self._store_document_metadata(document_metadata)
            
            # Store chunks in vector database
            self._store_chunks_in_vector_db(chunks)
            
            # Store chunk metadata
            self._store_chunk_metadata(chunks)
            
            return {
                'status': 'success',
                'file_path': file_path,
                'chunks_created': len(chunks),
                'document_id': chunks[0].document_id
            }
            
        except Exception as e:
            self.logger.error(f"Error ingesting {file_path}: {e}")
            return {
                'status': 'error',
                'file_path': file_path,
                'chunks_created': 0,
                'error': str(e)
            }
    
    def get_ingestion_status(self) -> Dict[str, Any]:
        """
        Get current ingestion status and statistics.
        
        Returns:
            Dictionary with current status information
        """
        try:
            conn = sqlite3.connect(self.metadata_db_path)
            cursor = conn.cursor()
            
            # Get document count
            cursor.execute("SELECT COUNT(*) FROM documents")
            document_count = cursor.fetchone()[0]
            
            # Get chunk count
            cursor.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cursor.fetchone()[0]
            
            # Get recent ingestions
            cursor.execute("""
                SELECT file_path, ingestion_date, chunk_count 
                FROM documents 
                ORDER BY ingestion_date DESC 
                LIMIT 10
            """)
            recent_ingestions = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_documents': document_count,
                'total_chunks': chunk_count,
                'recent_ingestions': [
                    {
                        'file_path': row[0],
                        'ingestion_date': row[1],
                        'chunk_count': row[2]
                    }
                    for row in recent_ingestions
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting ingestion status: {e}")
            return {
                'total_documents': 0,
                'total_chunks': 0,
                'recent_ingestions': [],
                'error': str(e)
            }
    
    def _discover_files(self) -> List[str]:
        """Discover files in the data directory."""
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
            self.logger.info(f"Created data directory: {self.data_path}")
            return []
        
        file_patterns = ['*.pdf', '*.txt', '*.md', '*.docx']
        file_paths = []
        
        data_dir = Path(self.data_path)
        for pattern in file_patterns:
            file_paths.extend(data_dir.glob(pattern))
        
        return [str(path) for path in file_paths]
    
    def _clear_existing_data(self):
        """Clear existing data from databases."""
        # Clear ChromaDB
        if os.path.exists(self.chroma_path):
            import shutil
            shutil.rmtree(self.chroma_path)
            self.logger.info("Cleared existing ChromaDB data")
        
        # Clear metadata database
        if os.path.exists(self.metadata_db_path):
            os.remove(self.metadata_db_path)
            self._initialize_metadata_db()
            self.logger.info("Cleared existing metadata database")
    
    def _initialize_metadata_db(self):
        """Initialize the metadata SQLite database."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                title TEXT,
                course_module TEXT,
                document_type TEXT,
                creation_date TEXT,
                page_count INTEGER,
                language TEXT,
                topics TEXT,  -- JSON array
                difficulty_level TEXT,
                file_path TEXT,
                file_size INTEGER,
                ingestion_date TEXT,
                chunk_count INTEGER
            )
        """)
        
        # Create chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT,
                content TEXT,
                content_type TEXT,
                hierarchical_context TEXT,  -- JSON array
                page_number INTEGER,
                position_in_document REAL,
                metadata TEXT,  -- JSON object
                FOREIGN KEY (document_id) REFERENCES documents (document_id)
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_content_type ON chunks(content_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_course_module ON documents(course_module)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_difficulty ON documents(difficulty_level)")
        
        conn.commit()
        conn.close()
    
    def _store_results(self, results: Dict[str, List[ProcessedChunk]]) -> Dict[str, Any]:
        """Store processing results in databases."""
        stats = {
            'files_processed': 0,
            'chunks_created': 0,
            'errors': [],
            'files_with_errors': 0
        }
        
        for file_path, chunks in results.items():
            try:
                if chunks:
                    # Extract document metadata from first chunk
                    document_metadata = self.document_processor.extract_metadata(file_path)
                    
                    # Store document metadata
                    self._store_document_metadata(document_metadata, len(chunks))
                    
                    # Store chunks in vector database
                    self._store_chunks_in_vector_db(chunks)
                    
                    # Store chunk metadata
                    self._store_chunk_metadata(chunks)
                    
                    stats['files_processed'] += 1
                    stats['chunks_created'] += len(chunks)
                else:
                    stats['errors'].append(f"No chunks created for {file_path}")
                    stats['files_with_errors'] += 1
                    
            except Exception as e:
                error_msg = f"Error storing results for {file_path}: {e}"
                self.logger.error(error_msg)
                stats['errors'].append(error_msg)
                stats['files_with_errors'] += 1
        
        return stats
    
    def _store_document_metadata(self, metadata: DocumentMetadata, chunk_count: int = 0):
        """Store document metadata in SQLite database."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO documents 
            (document_id, title, course_module, document_type, creation_date, 
             page_count, language, topics, difficulty_level, file_path, 
             file_size, ingestion_date, chunk_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.document_id,
            metadata.title,
            metadata.course_module,
            metadata.document_type,
            metadata.creation_date.isoformat(),
            metadata.page_count,
            metadata.language,
            json.dumps(metadata.topics),
            metadata.difficulty_level,
            metadata.file_path,
            metadata.file_size,
            datetime.now().isoformat(),
            chunk_count
        ))
        
        conn.commit()
        conn.close()
    
    def _store_chunks_in_vector_db(self, chunks: List[ProcessedChunk]):
        """Store chunks in ChromaDB vector database."""
        if not chunks:
            return
        
        # Prepare documents for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for chunk in chunks:
            documents.append(chunk.content)
            ids.append(chunk.chunk_id)
            
            # Prepare metadata for ChromaDB (must be simple types)
            chunk_metadata = {
                'document_id': chunk.document_id,
                'content_type': chunk.content_type.value,
                'page_number': chunk.page_number,
                'position_in_document': chunk.position_in_document,
                'hierarchical_context': json.dumps(chunk.hierarchical_context),
                'chunk_size': len(chunk.content)
            }
            
            # Add document-level metadata
            if chunk.metadata:
                for key, value in chunk.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        chunk_metadata[key] = value
                    else:
                        chunk_metadata[key] = str(value)
            
            metadatas.append(chunk_metadata)
        
        # Store in ChromaDB
        db = Chroma(
            persist_directory=self.chroma_path,
            embedding_function=self.embeddings
        )
        
        db.add_documents(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def _store_chunk_metadata(self, chunks: List[ProcessedChunk]):
        """Store detailed chunk metadata in SQLite database."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        for chunk in chunks:
            cursor.execute("""
                INSERT OR REPLACE INTO chunks 
                (chunk_id, document_id, content, content_type, hierarchical_context,
                 page_number, position_in_document, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.chunk_id,
                chunk.document_id,
                chunk.content,
                chunk.content_type.value,
                json.dumps(chunk.hierarchical_context),
                chunk.page_number,
                chunk.position_in_document,
                json.dumps(chunk.metadata)
            ))
        
        conn.commit()
        conn.close()


def create_enhanced_ingest_script():
    """Create an enhanced version of the original ingest.py script."""
    script_content = '''#!/usr/bin/env python3
"""
Enhanced document ingestion script with semantic chunking and metadata extraction.
"""
import sys
import argparse
from pathlib import Path
from .ingestion_pipeline import IngestionPipeline


def main():
    parser = argparse.ArgumentParser(description="Enhanced document ingestion pipeline")
    parser.add_argument("--data-path", default="data", help="Path to data directory")
    parser.add_argument("--chroma-path", default="chroma", help="Path to ChromaDB directory")
    parser.add_argument("--metadata-db", default="metadata.db", help="Path to metadata database")
    parser.add_argument("--embedding-model", default="llama3", help="Embedding model to use")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before ingestion")
    parser.add_argument("--files", nargs="+", help="Specific files to process")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = IngestionPipeline(
        data_path=args.data_path,
        chroma_path=args.chroma_path,
        metadata_db_path=args.metadata_db,
        embedding_model=args.embedding_model
    )
    
    # Check if data directory exists
    if not Path(args.data_path).exists():
        Path(args.data_path).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created data directory: {args.data_path}")
        print("Please add your documents to this directory and run the script again.")
        return
    
    # Run ingestion
    try:
        results = pipeline.ingest_documents(
            file_paths=args.files,
            show_progress=not args.quiet,
            clear_existing=args.clear
        )
        
        # Print results
        print("\\n🎉 Ingestion completed!")
        print(f"📊 Files processed: {results['files_processed']}")
        print(f"🧩 Chunks created: {results['chunks_created']}")
        print(f"⏱️  Duration: {results['duration']:.2f} seconds")
        
        if results['errors']:
            print(f"⚠️  Errors: {len(results['errors'])}")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(results['errors']) > 5:
                print(f"   ... and {len(results['errors']) - 5} more errors")
        
    except KeyboardInterrupt:
        print("\\n⏹️  Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
    
    with open("ingest_enhanced.py", "w") as f:
        f.write(script_content)
    
    # Make it executable
    import stat
    os.chmod("ingest_enhanced.py", stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)


if __name__ == "__main__":
    # Create the enhanced ingest script
    create_enhanced_ingest_script()
    print("Enhanced ingestion script created: ingest_enhanced.py")