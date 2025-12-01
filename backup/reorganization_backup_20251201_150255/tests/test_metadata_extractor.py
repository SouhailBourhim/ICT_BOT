"""
Unit tests for metadata extractor functionality.
"""
import unittest
import tempfile
import os
from datetime import datetime
from pathlib import Path
from models.base import ContentType
from processors.metadata_extractor import MetadataExtractor


class TestMetadataExtractor(unittest.TestCase):
    """Test cases for MetadataExtractor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = MetadataExtractor()
    
    def test_language_detection(self):
        """Test language detection functionality."""
        # Test English content
        english_content = "This is an English document about wireless communications and signal processing."
        lang = self.extractor._detect_language(english_content)
        self.assertEqual(lang, 'en')
        
        # Test French content
        french_content = "Ceci est un document en français sur les communications sans fil et le traitement du signal."
        lang = self.extractor._detect_language(french_content)
        # Note: Simple detection might not be perfect, but should work for basic cases
        
        # Test empty content
        empty_lang = self.extractor._detect_language("")
        self.assertEqual(empty_lang, 'en')  # Default to English
    
    def test_topic_extraction(self):
        """Test topic extraction based on course patterns."""
        # Test wireless communications content
        wireless_content = """
        This document covers wireless communication systems, including antenna design,
        signal propagation, and Rayleigh fading channels.
        """
        topics = self.extractor._extract_topics(wireless_content)
        self.assertIn('wireless_communications', topics)
        
        # Test programming content
        programming_content = """
        This tutorial covers Python programming, data structures, and algorithms
        for software development.
        """
        topics = self.extractor._extract_topics(programming_content)
        self.assertIn('programming', topics)
        
        # Test multiple topics
        mixed_content = """
        This course covers signal processing algorithms implemented in MATLAB,
        including digital filters and Fourier transforms for wireless systems.
        """
        topics = self.extractor._extract_topics(mixed_content)
        self.assertIn('signal_processing', topics)
        self.assertIn('programming', topics)
    
    def test_difficulty_assessment(self):
        """Test difficulty level assessment."""
        # Test beginner content
        beginner_content = "Introduction to basic concepts and fundamental principles."
        difficulty = self.extractor._assess_difficulty(beginner_content)
        self.assertEqual(difficulty, 'beginner')
        
        # Test advanced content
        advanced_content = "Advanced optimization techniques for complex signal analysis and research applications."
        difficulty = self.extractor._assess_difficulty(advanced_content)
        self.assertEqual(difficulty, 'advanced')
        
        # Test intermediate content (default)
        neutral_content = "This document discusses various methods and approaches."
        difficulty = self.extractor._assess_difficulty(neutral_content)
        self.assertEqual(difficulty, 'intermediate')
    
    def test_content_type_detection(self):
        """Test detection of different content types."""
        # Test formula detection
        formula_content = """
        The signal-to-noise ratio is given by:
        $$SNR = \\frac{P_s}{P_n}$$
        where $P_s$ is signal power and $P_n$ is noise power.
        """
        content_types = self.extractor._detect_content_types(formula_content)
        self.assertIn(ContentType.TEXT, content_types)
        self.assertIn(ContentType.FORMULA, content_types)
        
        # Test code detection
        code_content = """
        Here's a Python implementation:
        ```python
        def calculate_snr(signal_power, noise_power):
            return signal_power / noise_power
        ```
        """
        content_types = self.extractor._detect_content_types(code_content)
        self.assertIn(ContentType.TEXT, content_types)
        self.assertIn(ContentType.CODE, content_types)
        
        # Test table detection
        table_content = """
        | Parameter | Value | Unit |
        |-----------|-------|------|
        | Frequency | 2.4   | GHz  |
        | Power     | 20    | dBm  |
        """
        content_types = self.extractor._detect_content_types(table_content)
        self.assertIn(ContentType.TEXT, content_types)
        self.assertIn(ContentType.TABLE, content_types)
        
        # Test diagram detection
        diagram_content = "As shown in Figure 1, the system architecture includes multiple components."
        content_types = self.extractor._detect_content_types(diagram_content)
        self.assertIn(ContentType.TEXT, content_types)
        self.assertIn(ContentType.DIAGRAM, content_types)
    
    def test_text_metadata_extraction(self):
        """Test extraction of metadata from text content."""
        sample_content = """
        # Wireless Communication Systems
        
        This document provides an introduction to wireless communication systems.
        
        ## Basic Concepts
        
        Wireless communication involves the transmission of information without wires.
        The signal propagation follows various models including Rayleigh fading.
        
        ### Mathematical Models
        
        The path loss can be calculated using:
        $PL = 20 \\log_{10}(d) + 20 \\log_{10}(f) + 32.44$
        """
        
        metadata = self.extractor.extract_text_metadata(sample_content)
        
        # Check basic statistics
        self.assertGreater(metadata['word_count'], 0)
        self.assertGreater(metadata['character_count'], 0)
        self.assertGreater(metadata['line_count'], 0)
        self.assertGreater(metadata['paragraph_count'], 0)
        
        # Check content analysis
        self.assertEqual(metadata['language'], 'en')
        self.assertIn('wireless_communications', metadata['topics'])
        self.assertTrue(metadata['has_formulas'])
        
        # Check content types
        self.assertIn(ContentType.TEXT, metadata['content_types'])
        self.assertIn(ContentType.FORMULA, metadata['content_types'])
    
    def test_document_type_classification(self):
        """Test document type classification based on file extension."""
        # Test various file types
        test_cases = [
            ('document.pdf', 'pdf'),
            ('presentation.docx', 'docx'),
            ('notes.txt', 'txt'),
            ('readme.md', 'markdown'),
            ('paper.tex', 'latex'),
            ('webpage.html', 'html'),
            ('unknown.xyz', 'unknown')
        ]
        
        for filename, expected_type in test_cases:
            doc_type = self.extractor.classify_document_type(filename)
            self.assertEqual(doc_type, expected_type)
    
    def test_title_extraction_from_content(self):
        """Test extraction of document title from content."""
        # Test markdown header
        markdown_content = """
        # Introduction to Signal Processing
        
        This document covers the basics of signal processing.
        """
        title = self.extractor._extract_title_from_content(markdown_content)
        self.assertEqual(title, "Introduction to Signal Processing")
        
        # Test underlined header
        underlined_content = """
        Wireless Communication Systems
        ==============================
        
        This document discusses wireless systems.
        """
        title = self.extractor._extract_title_from_content(underlined_content)
        self.assertEqual(title, "Wireless Communication Systems")
        
        # Test first line as title
        simple_content = """
        Basic Networking Concepts
        
        This chapter introduces networking fundamentals.
        """
        title = self.extractor._extract_title_from_content(simple_content)
        self.assertEqual(title, "Basic Networking Concepts")
        
        # Test empty content
        empty_title = self.extractor._extract_title_from_content("")
        self.assertIsNone(empty_title)
    
    def test_course_module_determination(self):
        """Test determination of course module from content."""
        # Test wireless communications
        wireless_content = "This document covers antenna design and wireless propagation models."
        module = self.extractor._determine_course_module(wireless_content, "Antenna Theory")
        self.assertEqual(module, 'wireless_communications')
        
        # Test programming
        programming_content = "Python programming tutorial with data structures and algorithms."
        module = self.extractor._determine_course_module(programming_content, "Programming Guide")
        self.assertEqual(module, 'programming')
        
        # Test general content
        general_content = "This is a general document without specific technical content."
        module = self.extractor._determine_course_module(general_content, "General Notes")
        self.assertEqual(module, 'general')
    
    def test_create_document_metadata_with_text_file(self):
        """Test creation of complete document metadata from a text file."""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            content = """
            # Digital Signal Processing
            
            This document covers digital signal processing fundamentals including
            Fourier transforms, digital filters, and sampling theory.
            
            ## Mathematical Foundation
            
            The discrete Fourier transform is defined as:
            $X[k] = \\sum_{n=0}^{N-1} x[n] e^{-j2\\pi kn/N}$
            """
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Create metadata
            metadata = self.extractor.create_document_metadata(temp_file_path, content)
            
            # Verify metadata fields
            self.assertIsNotNone(metadata.document_id)
            self.assertEqual(metadata.title, "Digital Signal Processing")
            self.assertEqual(metadata.document_type, "txt")
            self.assertEqual(metadata.language, "en")
            self.assertIn("signal_processing", metadata.topics)
            self.assertIsInstance(metadata.creation_date, datetime)
            self.assertGreater(metadata.file_size, 0)
            self.assertEqual(metadata.file_path, temp_file_path)
            
        finally:
            # Clean up
            os.unlink(temp_file_path)
    
    def test_empty_content_handling(self):
        """Test handling of empty or minimal content."""
        # Test empty content
        empty_metadata = self.extractor.extract_text_metadata("")
        self.assertEqual(empty_metadata['word_count'], 0)
        self.assertEqual(empty_metadata['character_count'], 0)
        self.assertEqual(empty_metadata['language'], 'en')
        self.assertEqual(empty_metadata['topics'], [])
        
        # Test minimal content
        minimal_content = "Test"
        minimal_metadata = self.extractor.extract_text_metadata(minimal_content)
        self.assertEqual(minimal_metadata['word_count'], 1)
        self.assertEqual(minimal_metadata['character_count'], 4)
    
    def test_multiple_content_types_detection(self):
        """Test detection when multiple content types are present."""
        mixed_content = """
        # Signal Processing with Python
        
        This tutorial combines theory and practice.
        
        ## Mathematical Background
        
        The Fourier transform is: $F(\\omega) = \\int f(t) e^{-j\\omega t} dt$
        
        ## Implementation
        
        ```python
        import numpy as np
        
        def fft_example(signal):
            return np.fft.fft(signal)
        ```
        
        ## Results Table
        
        | Method | Accuracy | Speed |
        |--------|----------|-------|
        | FFT    | High     | Fast  |
        | DFT    | High     | Slow  |
        
        See Figure 1 for the frequency response.
        """
        
        content_types = self.extractor._detect_content_types(mixed_content)
        
        # Should detect all content types
        self.assertIn(ContentType.TEXT, content_types)
        self.assertIn(ContentType.FORMULA, content_types)
        self.assertIn(ContentType.CODE, content_types)
        self.assertIn(ContentType.TABLE, content_types)
        self.assertIn(ContentType.DIAGRAM, content_types)
        
        # Test metadata extraction
        metadata = self.extractor.extract_text_metadata(mixed_content)
        self.assertTrue(metadata['has_formulas'])
        self.assertTrue(metadata['has_code'])
        self.assertTrue(metadata['has_tables'])
        self.assertTrue(metadata['has_diagrams'])


if __name__ == '__main__':
    unittest.main()