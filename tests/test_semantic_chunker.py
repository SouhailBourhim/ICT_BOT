"""
Unit tests for semantic chunker functionality.
"""
import unittest
from datetime import datetime
from src.models.base import DocumentMetadata, ContentType
from src.processors.semantic_chunker import SemanticChunker, DocumentStructure


class TestSemanticChunker(unittest.TestCase):
    """Test cases for SemanticChunker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chunker = SemanticChunker(min_chunk_size=100, max_chunk_size=500)
        self.sample_metadata = DocumentMetadata(
            document_id="test-doc-1",
            title="Test Document",
            course_module="Test Module",
            document_type="pdf",
            creation_date=datetime.now(),
            page_count=1,
            language="en",
            topics=["testing"],
            difficulty_level="beginner",
            file_path="/test/path.pdf",
            file_size=1024
        )
    
    def test_header_extraction(self):
        """Test extraction of headers from document content."""
        content = """# Chapter 1: Introduction
        
This is the introduction paragraph.

## Section 1.1: Overview

This is an overview section.

### Subsection 1.1.1: Details

Detailed information here.

# Chapter 2: Methods

Second chapter content.
"""
        
        structure = self.chunker.analyze_structure(content)
        
        # Should find 4 headers
        self.assertEqual(len(structure.headers), 4)
        
        # Check header levels and titles
        expected_headers = [
            (1, "Chapter 1: Introduction"),
            (2, "Section 1.1: Overview"),
            (3, "Subsection 1.1.1: Details"),
            (1, "Chapter 2: Methods")
        ]
        
        for i, (expected_level, expected_title) in enumerate(expected_headers):
            actual_level, actual_title, _ = structure.headers[i]
            self.assertEqual(actual_level, expected_level)
            self.assertEqual(actual_title, expected_title)
    
    def test_content_type_detection(self):
        """Test detection of different content types."""
        # Test formula detection - small formula should be text
        formula_content = "The equation is E equals mc squared where E is energy and this is a much longer explanation to make the formula portion significantly smaller relative to the total text content in this paragraph."
        content_type = self.chunker._classify_section_content(formula_content)
        # Should detect as text since formula is small portion
        self.assertEqual(content_type, ContentType.TEXT)
        
        # Test with more formulas
        heavy_formula_content = """
        Mathematical formulas:
        $E = mc^2$
        $F = ma$
        $v = u + at$
        $s = ut + \\frac{1}{2}at^2$
        $$\\int_0^\\infty e^{-x} dx = 1$$
        """
        content_type = self.chunker._classify_section_content(heavy_formula_content)
        self.assertEqual(content_type, ContentType.FORMULA)
        
        # Test code detection
        code_content = """
        ```python
        def hello_world():
            print("Hello, World!")
            return True
        ```
        
        ```javascript
        function greet(name) {
            console.log(`Hello, ${name}!`);
        }
        ```
        """
        content_type = self.chunker._classify_section_content(code_content)
        self.assertEqual(content_type, ContentType.CODE)
    
    def test_adaptive_chunk_sizing(self):
        """Test adaptive chunk sizing based on content type."""
        base_content = "This is a test content for chunking."
        
        # Test different content types
        text_size = self.chunker.adaptive_chunk_size(base_content, ContentType.TEXT)
        formula_size = self.chunker.adaptive_chunk_size(base_content, ContentType.FORMULA)
        code_size = self.chunker.adaptive_chunk_size(base_content, ContentType.CODE)
        
        # Formula and code should get larger chunks
        self.assertGreater(formula_size, text_size)
        self.assertGreater(code_size, text_size)
        
        # All should be within bounds
        self.assertGreaterEqual(text_size, self.chunker.min_chunk_size)
        self.assertLessEqual(formula_size, self.chunker.max_chunk_size)
    
    def test_hierarchical_context_preservation(self):
        """Test preservation of hierarchical context in chunks."""
        content = """# Chapter 1: Introduction

This is the introduction to our course.

## Section 1.1: Basic Concepts

Here we discuss basic concepts that are fundamental to understanding.

### Subsection 1.1.1: Definitions

Important definitions are provided here.

## Section 1.2: Advanced Topics

Advanced material is covered in this section.
"""
        
        chunks = self.chunker.chunk_document(content, self.sample_metadata)
        
        # Should have multiple chunks
        self.assertGreater(len(chunks), 0)
        
        # Check that chunks have proper hierarchical context
        for chunk in chunks:
            self.assertIsInstance(chunk.hierarchical_context, list)
            self.assertGreater(len(chunk.hierarchical_context), 0)
        
        # Find a chunk that should have deep context (subsection level)
        deep_context_chunk = None
        for chunk in chunks:
            if "subsection 1.1.1" in chunk.content.lower() and len(chunk.hierarchical_context) >= 3:
                deep_context_chunk = chunk
                break
        
        if deep_context_chunk:
            # Should have context like ["Chapter 1: Introduction", "Section 1.1: Basic Concepts", "Subsection 1.1.1: Definitions"]
            self.assertGreaterEqual(len(deep_context_chunk.hierarchical_context), 2)
            # Verify the hierarchical structure
            self.assertIn("Chapter 1: Introduction", deep_context_chunk.hierarchical_context)
            self.assertIn("Section 1.1: Basic Concepts", deep_context_chunk.hierarchical_context)
    
    def test_chunk_metadata_accuracy(self):
        """Test accuracy of chunk metadata."""
        content = """# Test Chapter

This is a test chapter with some content that should be chunked appropriately.

The content includes multiple paragraphs to test the chunking algorithm.

## Test Section

This section has additional content to ensure proper metadata extraction.
"""
        
        chunks = self.chunker.chunk_document(content, self.sample_metadata)
        
        for chunk in chunks:
            # Check required fields
            self.assertIsNotNone(chunk.chunk_id)
            self.assertEqual(chunk.document_id, self.sample_metadata.document_id)
            self.assertIsNotNone(chunk.content)
            self.assertIsInstance(chunk.content_type, ContentType)
            self.assertIsInstance(chunk.hierarchical_context, list)
            self.assertIsInstance(chunk.position_in_document, float)
            self.assertGreaterEqual(chunk.position_in_document, 0.0)
            self.assertLessEqual(chunk.position_in_document, 1.0)
            
            # Check metadata
            self.assertIn("chunk_size", chunk.metadata)
            self.assertIn("content_classification", chunk.metadata)
            self.assertIn("context_depth", chunk.metadata)
            
            # Verify chunk size metadata matches actual content
            self.assertEqual(chunk.metadata["chunk_size"], len(chunk.content))
    
    def test_paragraph_extraction(self):
        """Test extraction of paragraph boundaries."""
        content = """First paragraph with some content.

Second paragraph after empty line.


Third paragraph after multiple empty lines.

Fourth paragraph."""
        
        structure = self.chunker.analyze_structure(content)
        
        # Should find 4 paragraphs
        self.assertEqual(len(structure.paragraphs), 4)
        
        # Check that paragraphs don't overlap
        for i in range(len(structure.paragraphs) - 1):
            current_end = structure.paragraphs[i][1]
            next_start = structure.paragraphs[i + 1][0]
            self.assertLessEqual(current_end, next_start)
    
    def test_section_extraction(self):
        """Test extraction of document sections."""
        content = """# Chapter 1
Content for chapter 1.

## Section 1.1
Content for section 1.1.

## Section 1.2
Content for section 1.2.

# Chapter 2
Content for chapter 2.
"""
        
        structure = self.chunker.analyze_structure(content)
        
        # Should find sections based on headers
        self.assertGreater(len(structure.sections), 0)
        
        # Check that sections cover the entire document
        if structure.sections:
            first_section_start = structure.sections[0][1]
            last_section_end = structure.sections[-1][2]
            
            self.assertEqual(first_section_start, 0)
            self.assertEqual(last_section_end, len(content))
    
    def test_empty_document_handling(self):
        """Test handling of empty or minimal documents."""
        # Test empty document
        empty_chunks = self.chunker.chunk_document("", self.sample_metadata)
        self.assertEqual(len(empty_chunks), 0)
        
        # Test minimal document
        minimal_content = "Just a short sentence."
        minimal_chunks = self.chunker.chunk_document(minimal_content, self.sample_metadata)
        self.assertEqual(len(minimal_chunks), 1)
        self.assertEqual(minimal_chunks[0].content, minimal_content)
    
    def test_large_document_chunking(self):
        """Test chunking of large documents that exceed max chunk size."""
        # Create a large document
        large_content = "This is a sentence. " * 100  # Should exceed max_chunk_size
        
        chunks = self.chunker.chunk_document(large_content, self.sample_metadata)
        
        # Should create multiple chunks
        self.assertGreater(len(chunks), 1)
        
        # Each chunk should be within size limits (except possibly the last one)
        for i, chunk in enumerate(chunks[:-1]):  # All but last chunk
            self.assertLessEqual(len(chunk.content), self.chunker.max_chunk_size)
        
        # All chunks should have minimum content (except possibly edge cases)
        for chunk in chunks:
            if chunk.content.strip():  # Non-empty chunks
                self.assertGreater(len(chunk.content.strip()), 0)


class TestDocumentStructure(unittest.TestCase):
    """Test cases for DocumentStructure class."""
    
    def test_document_structure_creation(self):
        """Test creation of DocumentStructure objects."""
        headers = [(1, "Chapter 1", 0), (2, "Section 1.1", 50)]
        sections = [("Chapter 1", 0, 100)]
        paragraphs = [(0, 30), (35, 70)]
        content_blocks = [("$E=mc^2$", 20, 28, ContentType.FORMULA)]
        
        structure = DocumentStructure(
            headers=headers,
            sections=sections,
            paragraphs=paragraphs,
            content_blocks=content_blocks
        )
        
        self.assertEqual(structure.headers, headers)
        self.assertEqual(structure.sections, sections)
        self.assertEqual(structure.paragraphs, paragraphs)
        self.assertEqual(structure.content_blocks, content_blocks)


if __name__ == '__main__':
    # Run tests
    unittest.main()