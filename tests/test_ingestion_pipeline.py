"""
Integration tests for the enhanced ingestion pipeline.
"""
import unittest
import tempfile
import os
import shutil
import sqlite3
from pathlib import Path
from src.processors.ingestion_pipeline import IngestionPipeline
from src.processors.document_processor import DocumentProcessor


class TestIngestionPipeline(unittest.TestCase):
    """Integration test cases for IngestionPipeline."""
    
    def setUp(self):
        """Set up test fixtures with temporary directories."""
        self.test_dir = tempfile.mkdtemp()
        self.data_path = os.path.join(self.test_dir, "data")
        self.chroma_path = os.path.join(self.test_dir, "chroma")
        self.metadata_db_path = os.path.join(self.test_dir, "metadata.db")
        
        # Create data directory
        os.makedirs(self.data_path, exist_ok=True)
        
        # Create test documents
        self._create_test_documents()
        
        # Initialize pipeline
        self.pipeline = IngestionPipeline(
            data_path=self.data_path,
            chroma_path=self.chroma_path,
            metadata_db_path=self.metadata_db_path,
            embedding_model="llama3"
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_documents(self):
        """Create test documents for ingestion."""
        # Create a test text document
        text_content = """
        # Wireless Communication Systems
        
        This document covers the fundamentals of wireless communication systems.
        
        ## Signal Propagation
        
        Radio waves propagate through various media and experience different types of fading.
        
        ### Rayleigh Fading
        
        Rayleigh fading occurs when there is no direct line-of-sight path.
        The signal amplitude follows a Rayleigh distribution.
        
        ## Mathematical Models
        
        The path loss can be modeled as:
        $PL = 20 \\log_{10}(d) + 20 \\log_{10}(f) + 32.44$
        
        Where d is distance and f is frequency.
        """
        
        with open(os.path.join(self.data_path, "wireless_systems.txt"), "w") as f:
            f.write(text_content)
        
        # Create another test document
        programming_content = """
        # Python Programming Guide
        
        This guide covers Python programming fundamentals.
        
        ## Data Structures
        
        Python provides several built-in data structures:
        
        ```python
        # Lists
        my_list = [1, 2, 3, 4, 5]
        
        # Dictionaries
        my_dict = {'key': 'value', 'number': 42}
        
        # Sets
        my_set = {1, 2, 3, 4, 5}
        ```
        
        ## Algorithms
        
        Here's a simple sorting algorithm:
        
        ```python
        def bubble_sort(arr):
            n = len(arr)
            for i in range(n):
                for j in range(0, n-i-1):
                    if arr[j] > arr[j+1]:
                        arr[j], arr[j+1] = arr[j+1], arr[j]
            return arr
        ```
        """
        
        with open(os.path.join(self.data_path, "python_guide.md"), "w") as f:
            f.write(programming_content)
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization and database setup."""
        # Check that metadata database was created
        self.assertTrue(os.path.exists(self.metadata_db_path))
        
        # Check database schema
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        # Check documents table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Check chunks table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chunks'")
        self.assertIsNotNone(cursor.fetchone())
        
        conn.close()
    
    def test_document_discovery(self):
        """Test automatic document discovery."""
        file_paths = self.pipeline._discover_files()
        
        # Should find both test documents
        self.assertEqual(len(file_paths), 2)
        
        # Check that both files are found
        file_names = [os.path.basename(path) for path in file_paths]
        self.assertIn("wireless_systems.txt", file_names)
        self.assertIn("python_guide.md", file_names)
    
    def test_single_document_ingestion(self):
        """Test ingestion of a single document."""
        file_path = os.path.join(self.data_path, "wireless_systems.txt")
        
        result = self.pipeline.ingest_single_document(file_path)
        
        # Check result
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['chunks_created'], 0)
        self.assertIsNotNone(result['document_id'])
        
        # Check that data was stored in metadata database
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        self.assertEqual(doc_count, 1)
        
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]
        self.assertGreater(chunk_count, 0)
        
        conn.close()
    
    def test_batch_document_ingestion(self):
        """Test batch ingestion of multiple documents."""
        results = self.pipeline.ingest_documents(show_progress=False)
        
        # Check results
        self.assertEqual(results['status'], 'completed')
        self.assertEqual(results['files_processed'], 2)
        self.assertGreater(results['chunks_created'], 0)
        self.assertEqual(len(results['errors']), 0)
        
        # Check database contents
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        self.assertEqual(doc_count, 2)
        
        cursor.execute("SELECT title, course_module FROM documents")
        documents = cursor.fetchall()
        
        # Check document metadata
        titles = [doc[0] for doc in documents]
        modules = [doc[1] for doc in documents]
        
        self.assertIn("Wireless Communication Systems", titles)
        self.assertIn("Python Programming Guide", titles)
        self.assertIn("wireless_communications", modules)
        self.assertIn("programming", modules)
        
        conn.close()
    
    def test_ingestion_status(self):
        """Test ingestion status reporting."""
        # First ingest some documents
        self.pipeline.ingest_documents(show_progress=False)
        
        # Get status
        status = self.pipeline.get_ingestion_status()
        
        # Check status information
        self.assertEqual(status['total_documents'], 2)
        self.assertGreater(status['total_chunks'], 0)
        self.assertEqual(len(status['recent_ingestions']), 2)
        
        # Check recent ingestions structure
        for ingestion in status['recent_ingestions']:
            self.assertIn('file_path', ingestion)
            self.assertIn('ingestion_date', ingestion)
            self.assertIn('chunk_count', ingestion)
    
    def test_clear_existing_data(self):
        """Test clearing existing data."""
        # First ingest some documents
        self.pipeline.ingest_documents(show_progress=False)
        
        # Verify data exists
        status = self.pipeline.get_ingestion_status()
        self.assertGreater(status['total_documents'], 0)
        
        # Clear data
        self.pipeline._clear_existing_data()
        
        # Verify data is cleared
        status = self.pipeline.get_ingestion_status()
        self.assertEqual(status['total_documents'], 0)
        self.assertEqual(status['total_chunks'], 0)
    
    def test_error_handling(self):
        """Test error handling for problematic files."""
        # Create a file that will cause processing errors
        bad_file_path = os.path.join(self.data_path, "bad_file.txt")
        with open(bad_file_path, "wb") as f:
            f.write(b'\x00\x01\x02\x03')  # Binary content that might cause issues
        
        # Try to ingest
        results = self.pipeline.ingest_documents(show_progress=False)
        
        # Should complete but may have some errors
        self.assertEqual(results['status'], 'completed')
        # Should still process the good files
        self.assertGreaterEqual(results['files_processed'], 2)
    
    def test_metadata_extraction_accuracy(self):
        """Test accuracy of metadata extraction during ingestion."""
        # Ingest documents
        self.pipeline.ingest_documents(show_progress=False)
        
        # Check extracted metadata
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT title, course_module, difficulty_level, topics 
            FROM documents 
            WHERE title = 'Wireless Communication Systems'
        """)
        
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        
        title, course_module, difficulty_level, topics = result
        self.assertEqual(title, "Wireless Communication Systems")
        self.assertEqual(course_module, "wireless_communications")
        # Topics should be a JSON array containing wireless_communications
        import json
        topics_list = json.loads(topics)
        self.assertIn("wireless_communications", topics_list)
        
        conn.close()
    
    def test_hierarchical_context_preservation(self):
        """Test that hierarchical context is preserved during ingestion."""
        # Ingest documents
        self.pipeline.ingest_documents(show_progress=False)
        
        # Check chunk hierarchical context
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT hierarchical_context, content 
            FROM chunks 
            WHERE content LIKE '%Rayleigh fading%'
        """)
        
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        
        hierarchical_context, content = result
        import json
        context_list = json.loads(hierarchical_context)
        
        # Should have hierarchical context
        self.assertGreater(len(context_list), 0)
        # Should include section information
        self.assertTrue(any("Signal Propagation" in ctx for ctx in context_list))
        
        conn.close()


class TestDocumentProcessor(unittest.TestCase):
    """Test cases for DocumentProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = DocumentProcessor()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_process_text_document(self):
        """Test processing of text documents."""
        # Create test file
        content = """
        # Test Document
        
        This is a test document with multiple sections.
        
        ## Section 1
        
        Content for section 1.
        
        ## Section 2
        
        Content for section 2 with some formulas: $E = mc^2$
        """
        
        file_path = os.path.join(self.test_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write(content)
        
        # Process document
        chunks = self.processor.process_document(file_path)
        
        # Verify results
        self.assertGreater(len(chunks), 0)
        
        # Check chunk properties
        for chunk in chunks:
            self.assertIsNotNone(chunk.chunk_id)
            self.assertIsNotNone(chunk.document_id)
            self.assertIsNotNone(chunk.content)
            self.assertIsInstance(chunk.hierarchical_context, list)
            self.assertGreater(len(chunk.hierarchical_context), 0)
    
    def test_batch_processing(self):
        """Test batch processing of multiple documents."""
        # Create multiple test files
        files = []
        for i in range(3):
            content = f"""
            # Document {i+1}
            
            This is test document number {i+1}.
            
            ## Section A
            
            Content for section A in document {i+1}.
            """
            
            file_path = os.path.join(self.test_dir, f"doc_{i+1}.txt")
            with open(file_path, "w") as f:
                f.write(content)
            files.append(file_path)
        
        # Process batch
        results = self.processor.process_batch(files)
        
        # Verify results
        self.assertEqual(len(results), 3)
        
        for file_path, chunks in results.items():
            self.assertGreater(len(chunks), 0)
            self.assertIn(file_path, files)


if __name__ == '__main__':
    unittest.main()