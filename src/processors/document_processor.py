"""
Enhanced document processor that combines semantic chunking and metadata extraction.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from src.models.base import ProcessedChunk, DocumentMetadata
from .interfaces import DocumentProcessorInterface
from .semantic_chunker import SemanticChunker
from .metadata_extractor import MetadataExtractor


class DocumentProcessor(DocumentProcessorInterface):
    """
    Enhanced document processor that provides comprehensive document processing.
    
    Features:
    - Semantic chunking with hierarchical context
    - Comprehensive metadata extraction
    - Content type detection and classification
    - Error handling and progress tracking
    - Support for multiple document formats
    """
    
    def __init__(self, min_chunk_size: int = 500, max_chunk_size: int = 2000):
        """
        Initialize the document processor.
        
        Args:
            min_chunk_size: Minimum chunk size in characters
            max_chunk_size: Maximum chunk size in characters
        """
        self.semantic_chunker = SemanticChunker(min_chunk_size, max_chunk_size)
        self.metadata_extractor = MetadataExtractor()
        self.logger = logging.getLogger(__name__)
    
    def process_document(self, file_path: str) -> List[ProcessedChunk]:
        """
        Process a document and return enhanced chunks with metadata.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of processed chunks with complete metadata
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is not supported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Extract document metadata
            self.logger.info(f"Processing document: {file_path}")
            document_metadata = self.extract_metadata(file_path)
            
            # Extract text content
            content = self._extract_text_content(file_path, document_metadata)
            
            if not content or not content.strip():
                self.logger.warning(f"No text content extracted from {file_path}")
                return []
            
            # Create semantic chunks
            chunks = self.semantic_chunker.chunk_document(content, document_metadata)
            
            # Enhance chunks with additional processing
            enhanced_chunks = self._enhance_chunks(chunks, document_metadata)
            
            self.logger.info(f"Successfully processed {file_path}: {len(enhanced_chunks)} chunks created")
            return enhanced_chunks
            
        except Exception as e:
            self.logger.error(f"Error processing document {file_path}: {e}")
            raise
    
    def extract_metadata(self, file_path: str) -> DocumentMetadata:
        """
        Extract comprehensive metadata from a document.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Complete DocumentMetadata object
        """
        return self.metadata_extractor.create_document_metadata(file_path)
    
    def detect_content_type(self, chunk: str):
        """
        Detect the content type of a chunk.
        
        Args:
            chunk: Text chunk to analyze
            
        Returns:
            ContentType enum value
        """
        return self.semantic_chunker._classify_section_content(chunk)
    
    def preserve_formatting(self, chunk: str):
        """
        Preserve formatting in a chunk (placeholder for future enhancement).
        
        Args:
            chunk: Text chunk to process
            
        Returns:
            FormattedChunk object
        """
        # This is a placeholder implementation
        # In the future, this could handle LaTeX, markdown, etc.
        from src.models.base import FormattedChunk, ContentType
        
        content_type = self.detect_content_type(chunk)
        
        return FormattedChunk(
            content=chunk,
            formatting_metadata={
                'original_format': 'text',
                'preserved_elements': []
            },
            content_type=content_type,
            preserved_elements=[]
        )
    
    def process_batch(self, file_paths: List[str], 
                     progress_callback: Optional[callable] = None) -> Dict[str, List[ProcessedChunk]]:
        """
        Process multiple documents in batch.
        
        Args:
            file_paths: List of file paths to process
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary mapping file paths to their processed chunks
        """
        results = {}
        total_files = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            try:
                chunks = self.process_document(file_path)
                results[file_path] = chunks
                
                if progress_callback:
                    progress_callback(i + 1, total_files, file_path, len(chunks))
                    
            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {e}")
                results[file_path] = []
                
                if progress_callback:
                    progress_callback(i + 1, total_files, file_path, 0, error=str(e))
        
        return results
    
    def _extract_text_content(self, file_path: str, metadata: DocumentMetadata) -> str:
        """
        Extract text content from various document formats.
        
        Args:
            file_path: Path to the document file
            metadata: Document metadata
            
        Returns:
            Extracted text content
        """
        document_type = metadata.document_type
        
        if document_type == 'pdf':
            return self._extract_pdf_content(file_path)
        elif document_type in ['txt', 'md', 'markdown']:
            return self._extract_text_file_content(file_path)
        elif document_type in ['docx']:
            return self._extract_docx_content(file_path)
        else:
            # Try to read as text file
            try:
                return self._extract_text_file_content(file_path)
            except Exception:
                raise ValueError(f"Unsupported document type: {document_type}")
    
    def _extract_pdf_content(self, file_path: str) -> str:
        """Extract text content from PDF files."""
        try:
            import pypdf
            
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                content = ""
                
                for page in pdf_reader.pages:
                    try:
                        content += page.extract_text() + "\n"
                    except Exception as e:
                        self.logger.warning(f"Error extracting text from page in {file_path}: {e}")
                        continue
                
                return content
                
        except Exception as e:
            self.logger.error(f"Error extracting PDF content from {file_path}: {e}")
            return ""
    
    def _extract_text_file_content(self, file_path: str) -> str:
        """Extract content from text files."""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        return file.read()
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, read as binary and decode with errors='ignore'
            with open(file_path, 'rb') as file:
                return file.read().decode('utf-8', errors='ignore')
                
        except Exception as e:
            self.logger.error(f"Error reading text file {file_path}: {e}")
            return ""
    
    def _extract_docx_content(self, file_path: str) -> str:
        """Extract content from DOCX files (placeholder implementation)."""
        # This would require python-docx library
        # For now, return empty string with a warning
        self.logger.warning(f"DOCX processing not implemented for {file_path}")
        return ""
    
    def _enhance_chunks(self, chunks: List[ProcessedChunk], 
                       document_metadata: DocumentMetadata) -> List[ProcessedChunk]:
        """
        Enhance chunks with additional metadata and processing.
        
        Args:
            chunks: List of processed chunks
            document_metadata: Document metadata
            
        Returns:
            Enhanced chunks with additional metadata
        """
        enhanced_chunks = []
        
        for chunk in chunks:
            # Add document-level metadata to chunk metadata
            chunk.metadata.update({
                'document_title': document_metadata.title,
                'document_course_module': document_metadata.course_module,
                'document_topics': document_metadata.topics,
                'document_difficulty': document_metadata.difficulty_level,
                'document_language': document_metadata.language,
                'document_type': document_metadata.document_type,
                'document_page_count': document_metadata.page_count
            })
            
            # Calculate relative position within document
            if document_metadata.page_count > 1:
                estimated_page = int(chunk.position_in_document * document_metadata.page_count) + 1
                chunk.page_number = min(estimated_page, document_metadata.page_count)
            
            enhanced_chunks.append(chunk)
        
        return enhanced_chunks


class BatchProcessor:
    """
    Utility class for batch processing of documents with progress tracking.
    """
    
    def __init__(self, document_processor: DocumentProcessor):
        self.document_processor = document_processor
        self.logger = logging.getLogger(__name__)
    
    def process_directory(self, directory_path: str, 
                         file_patterns: List[str] = None,
                         recursive: bool = True,
                         progress_callback: Optional[callable] = None) -> Dict[str, List[ProcessedChunk]]:
        """
        Process all documents in a directory.
        
        Args:
            directory_path: Path to the directory
            file_patterns: List of file patterns to match (e.g., ['*.pdf', '*.txt'])
            recursive: Whether to search subdirectories
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping file paths to their processed chunks
        """
        if file_patterns is None:
            file_patterns = ['*.pdf', '*.txt', '*.md', '*.docx']
        
        # Find all matching files
        directory = Path(directory_path)
        file_paths = []
        
        for pattern in file_patterns:
            if recursive:
                file_paths.extend(directory.rglob(pattern))
            else:
                file_paths.extend(directory.glob(pattern))
        
        # Convert to strings
        file_paths = [str(path) for path in file_paths]
        
        self.logger.info(f"Found {len(file_paths)} files to process in {directory_path}")
        
        # Process files
        return self.document_processor.process_batch(file_paths, progress_callback)
    
    def create_progress_tracker(self, show_progress: bool = True):
        """
        Create a progress tracking callback function.
        
        Args:
            show_progress: Whether to show progress output
            
        Returns:
            Progress callback function
        """
        def progress_callback(current: int, total: int, file_path: str, 
                            chunk_count: int, error: str = None):
            if show_progress:
                percentage = (current / total) * 100
                status = f"Error: {error}" if error else f"{chunk_count} chunks"
                print(f"[{current}/{total}] ({percentage:.1f}%) {Path(file_path).name}: {status}")
        
        return progress_callback if show_progress else None