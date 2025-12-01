"""
Abstract interfaces for document processing components.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from models.base import ProcessedChunk, DocumentMetadata, ContentType, FormattedChunk


class DocumentProcessorInterface(ABC):
    """Abstract interface for document processors."""
    
    @abstractmethod
    def process_document(self, file_path: str) -> List[ProcessedChunk]:
        """Process a document and return chunks."""
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: str) -> DocumentMetadata:
        """Extract metadata from a document."""
        pass
    
    @abstractmethod
    def detect_content_type(self, chunk: str) -> ContentType:
        """Detect the content type of a chunk."""
        pass
    
    @abstractmethod
    def preserve_formatting(self, chunk: str) -> FormattedChunk:
        """Preserve formatting in a chunk."""
        pass


class SemanticChunkerInterface(ABC):
    """Abstract interface for semantic chunking."""
    
    @abstractmethod
    def chunk_document(self, content: str, metadata: DocumentMetadata) -> List[ProcessedChunk]:
        """Chunk document based on semantic structure."""
        pass
    
    @abstractmethod
    def analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure."""
        pass
    
    @abstractmethod
    def adaptive_chunk_size(self, content: str, content_type: ContentType) -> int:
        """Determine optimal chunk size based on content type."""
        pass


class MetadataExtractorInterface(ABC):
    """Abstract interface for metadata extraction."""
    
    @abstractmethod
    def extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF files."""
        pass
    
    @abstractmethod
    def extract_text_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from text content."""
        pass
    
    @abstractmethod
    def classify_document_type(self, file_path: str) -> str:
        """Classify document type."""
        pass


class EmbeddingGeneratorInterface(ABC):
    """Abstract interface for embedding generation."""
    
    @abstractmethod
    def generate_embeddings(self, chunks: List[ProcessedChunk]) -> List[ProcessedChunk]:
        """Generate embeddings for chunks."""
        pass
    
    @abstractmethod
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for a query."""
        pass