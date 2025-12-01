"""
Metadata extraction implementation for document processing.
"""
import os
import re
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import pypdf
from models.base import DocumentMetadata, ContentType
from processors.interfaces import MetadataExtractorInterface


class MetadataExtractor(MetadataExtractorInterface):
    """
    Enhanced metadata extractor for various document types.
    
    Features:
    - PDF metadata extraction using pypdf
    - Content analysis for topic extraction
    - Document type classification
    - Language detection
    - Difficulty level assessment
    """
    
    def __init__(self):
        # Course module patterns for INPT Smart ICT curriculum
        self.course_patterns = {
            'wireless_communications': [
                r'wireless.*communication', r'mobile.*communication', r'cellular',
                r'antenna', r'propagation', r'fading', r'rayleigh', r'rician'
            ],
            'signal_processing': [
                r'signal.*processing', r'digital.*signal', r'fourier', r'transform',
                r'filter', r'convolution', r'sampling'
            ],
            'networking': [
                r'network', r'protocol', r'tcp', r'ip', r'routing', r'switching',
                r'ethernet', r'wifi'
            ],
            'programming': [
                r'programming', r'algorithm', r'data.*structure', r'software',
                r'python', r'java', r'c\+\+', r'matlab'
            ],
            'mathematics': [
                r'mathematics', r'calculus', r'linear.*algebra', r'statistics',
                r'probability', r'matrix', r'vector'
            ]
        }
        
        # Difficulty indicators
        self.difficulty_indicators = {
            'beginner': [
                r'introduction', r'basic', r'fundamental', r'overview',
                r'getting.*started', r'primer'
            ],
            'intermediate': [
                r'advanced.*basic', r'intermediate', r'practical', r'application',
                r'implementation', r'case.*study'
            ],
            'advanced': [
                r'advanced', r'complex', r'sophisticated', r'research',
                r'optimization', r'analysis', r'theory'
            ]
        }
        
        # Language patterns
        self.language_patterns = {
            'en': [r'[a-zA-Z]', r'\bthe\b', r'\band\b', r'\bof\b', r'\bin\b'],
            'fr': [r'\ble\b', r'\bla\b', r'\bde\b', r'\bet\b', r'\bdu\b'],
            'ar': [r'[\u0600-\u06FF]', r'\u0627\u0644', r'\u0641\u064A']  # Arabic script
        }
    
    def extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from PDF files using pypdf.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {
            'title': None,
            'author': None,
            'subject': None,
            'creator': None,
            'producer': None,
            'creation_date': None,
            'modification_date': None,
            'page_count': 0,
            'file_size': 0,
            'text_content': ""
        }
        
        try:
            # Get file stats
            file_stats = os.stat(file_path)
            metadata['file_size'] = file_stats.st_size
            metadata['modification_date'] = datetime.fromtimestamp(file_stats.st_mtime)
            
            # Extract PDF metadata and content
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                # Basic PDF info
                metadata['page_count'] = len(pdf_reader.pages)
                
                # PDF metadata
                if pdf_reader.metadata:
                    pdf_meta = pdf_reader.metadata
                    metadata['title'] = pdf_meta.get('/Title', '').strip() if pdf_meta.get('/Title') else None
                    metadata['author'] = pdf_meta.get('/Author', '').strip() if pdf_meta.get('/Author') else None
                    metadata['subject'] = pdf_meta.get('/Subject', '').strip() if pdf_meta.get('/Subject') else None
                    metadata['creator'] = pdf_meta.get('/Creator', '').strip() if pdf_meta.get('/Creator') else None
                    metadata['producer'] = pdf_meta.get('/Producer', '').strip() if pdf_meta.get('/Producer') else None
                    
                    # Creation date
                    if pdf_meta.get('/CreationDate'):
                        try:
                            # pypdf date format: D:YYYYMMDDHHmmSSOHH'mm'
                            date_str = str(pdf_meta.get('/CreationDate'))
                            if date_str.startswith('D:'):
                                date_str = date_str[2:16]  # Extract YYYYMMDDHHMMSS
                                metadata['creation_date'] = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                        except (ValueError, TypeError):
                            pass
                
                # Extract text content from first few pages for analysis
                text_content = ""
                max_pages_for_analysis = min(5, len(pdf_reader.pages))
                
                for page_num in range(max_pages_for_analysis):
                    try:
                        page = pdf_reader.pages[page_num]
                        text_content += page.extract_text() + "\n"
                    except Exception:
                        continue  # Skip problematic pages
                
                metadata['text_content'] = text_content
                
        except Exception as e:
            # Log error but continue with available metadata
            print(f"Error extracting PDF metadata from {file_path}: {e}")
        
        return metadata
    
    def extract_text_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract metadata from text content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {
            'word_count': 0,
            'character_count': 0,
            'line_count': 0,
            'paragraph_count': 0,
            'topics': [],
            'language': 'en',
            'difficulty_level': 'intermediate',
            'content_types': [],
            'has_formulas': False,
            'has_code': False,
            'has_tables': False,
            'has_diagrams': False
        }
        
        if not content:
            return metadata
        
        # Basic text statistics
        metadata['character_count'] = len(content)
        metadata['word_count'] = len(content.split())
        metadata['line_count'] = len(content.split('\n'))
        
        # Count paragraphs (non-empty lines separated by empty lines)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        metadata['paragraph_count'] = len(paragraphs)
        
        # Detect language
        metadata['language'] = self._detect_language(content)
        
        # Extract topics based on course patterns
        metadata['topics'] = self._extract_topics(content)
        
        # Assess difficulty level
        metadata['difficulty_level'] = self._assess_difficulty(content)
        
        # Detect content types
        content_types = self._detect_content_types(content)
        metadata['content_types'] = content_types
        metadata['has_formulas'] = ContentType.FORMULA in content_types
        metadata['has_code'] = ContentType.CODE in content_types
        metadata['has_tables'] = ContentType.TABLE in content_types
        metadata['has_diagrams'] = ContentType.DIAGRAM in content_types
        
        return metadata
    
    def classify_document_type(self, file_path: str) -> str:
        """
        Classify document type based on file extension and content.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Document type string
        """
        file_extension = Path(file_path).suffix.lower()
        
        type_mapping = {
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.doc': 'doc',
            '.txt': 'txt',
            '.md': 'markdown',
            '.tex': 'latex',
            '.html': 'html',
            '.htm': 'html'
        }
        
        return type_mapping.get(file_extension, 'unknown')
    
    def create_document_metadata(self, file_path: str, content: str = None) -> DocumentMetadata:
        """
        Create complete DocumentMetadata object from file and content analysis.
        
        Args:
            file_path: Path to the document file
            content: Optional text content (will be extracted if not provided)
            
        Returns:
            Complete DocumentMetadata object
        """
        # Basic file information
        file_stats = os.stat(file_path)
        document_type = self.classify_document_type(file_path)
        
        # Extract PDF-specific metadata if applicable
        pdf_metadata = {}
        if document_type == 'pdf':
            pdf_metadata = self.extract_pdf_metadata(file_path)
            if not content:
                content = pdf_metadata.get('text_content', '')
        
        # Extract text metadata
        text_metadata = self.extract_text_metadata(content or '')
        
        # Determine title
        title = (pdf_metadata.get('title') or 
                self._extract_title_from_content(content or '') or 
                Path(file_path).stem)
        
        # Determine course module
        course_module = self._determine_course_module(content or '', title)
        
        return DocumentMetadata(
            document_id=str(uuid.uuid4()),
            title=title,
            course_module=course_module,
            document_type=document_type,
            creation_date=pdf_metadata.get('creation_date') or datetime.fromtimestamp(file_stats.st_ctime),
            page_count=pdf_metadata.get('page_count', 1),
            language=text_metadata['language'],
            topics=text_metadata['topics'],
            difficulty_level=text_metadata['difficulty_level'],
            file_path=file_path,
            file_size=file_stats.st_size
        )
    
    def _detect_language(self, content: str) -> str:
        """Detect the primary language of the content."""
        if not content:
            return 'en'
        
        # Simple language detection based on character patterns
        scores = {}
        
        for lang, patterns in self.language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                score += matches
            scores[lang] = score
        
        # Return language with highest score, default to English
        return max(scores, key=scores.get) if scores else 'en'
    
    def _extract_topics(self, content: str) -> List[str]:
        """Extract topics based on course module patterns."""
        topics = []
        content_lower = content.lower()
        
        for module, patterns in self.course_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    topics.append(module)
                    break  # Only add each module once
        
        return topics
    
    def _assess_difficulty(self, content: str) -> str:
        """Assess difficulty level based on content indicators."""
        content_lower = content.lower()
        scores = {'beginner': 0, 'intermediate': 0, 'advanced': 0}
        
        for level, patterns in self.difficulty_indicators.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower))
                scores[level] += matches
        
        # Default to intermediate if no clear indicators
        if all(score == 0 for score in scores.values()):
            return 'intermediate'
        
        return max(scores, key=scores.get)
    
    def _detect_content_types(self, content: str) -> List[ContentType]:
        """Detect different content types present in the document."""
        content_types = [ContentType.TEXT]  # Always has text
        
        # Formula patterns
        formula_patterns = [
            r'\$[^$]+\$',  # LaTeX inline math
            r'\$\$[^$]+\$\$',  # LaTeX display math
            r'\\begin\{equation\}.*?\\end\{equation\}',
            r'\\begin\{align\}.*?\\end\{align\}',
            r'[a-zA-Z]\s*=\s*[^,\n]+',  # Simple equations
            r'∫|∑|∏|√|±|≤|≥|≠|≈|∞'  # Mathematical symbols
        ]
        
        for pattern in formula_patterns:
            if re.search(pattern, content, re.DOTALL):
                content_types.append(ContentType.FORMULA)
                break
        
        # Code patterns
        code_patterns = [
            r'```[\s\S]*?```',  # Markdown code blocks
            r'`[^`]+`',  # Inline code
            r'def\s+\w+\s*\(',  # Python functions
            r'class\s+\w+\s*[:\(]',  # Python classes
            r'import\s+\w+',  # Import statements
            r'#include\s*<[^>]+>',  # C/C++ includes
            r'function\s+\w+\s*\(',  # JavaScript functions
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, content, re.DOTALL):
                content_types.append(ContentType.CODE)
                break
        
        # Table patterns
        table_patterns = [
            r'\|.*\|.*\|',  # Markdown tables
            r'\\begin\{table\}.*?\\end\{table\}',  # LaTeX tables
            r'\\begin\{tabular\}.*?\\end\{tabular\}',  # LaTeX tabular
        ]
        
        for pattern in table_patterns:
            if re.search(pattern, content, re.DOTALL):
                content_types.append(ContentType.TABLE)
                break
        
        # Diagram patterns (references to figures, diagrams, etc.)
        diagram_patterns = [
            r'figure\s+\d+',
            r'fig\.\s*\d+',
            r'diagram',
            r'\\begin\{figure\}.*?\\end\{figure\}',
            r'\\includegraphics',
        ]
        
        for pattern in diagram_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                content_types.append(ContentType.DIAGRAM)
                break
        
        return content_types
    
    def _extract_title_from_content(self, content: str) -> Optional[str]:
        """Extract title from document content."""
        if not content:
            return None
        
        lines = content.split('\n')
        
        # Look for markdown-style headers
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('#'):
                # Remove markdown header syntax
                title = re.sub(r'^#+\s*', '', line).strip()
                if title:
                    return title
            elif line and len(line) < 100:  # Potential title line
                # Check if next line is underline (=== or ---)
                line_idx = None
                for idx, l in enumerate(lines):
                    if l.strip() == line:
                        line_idx = idx
                        break
                
                if line_idx is not None and line_idx + 1 < len(lines):
                    next_line = lines[line_idx + 1].strip()
                    if next_line and all(c in '=-' for c in next_line):
                        return line.strip()
        
        # Look for first non-empty line as potential title
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 100:
                return line
        
        return None
    
    def _determine_course_module(self, content: str, title: str) -> str:
        """Determine course module based on content and title analysis."""
        combined_text = f"{title} {content}".lower()
        
        # Score each module based on keyword matches
        module_scores = {}
        for module, patterns in self.course_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, combined_text))
                score += matches
            module_scores[module] = score
        
        # Return module with highest score, or 'general' if no clear match
        if module_scores and max(module_scores.values()) > 0:
            return max(module_scores, key=module_scores.get)
        else:
            return 'general'