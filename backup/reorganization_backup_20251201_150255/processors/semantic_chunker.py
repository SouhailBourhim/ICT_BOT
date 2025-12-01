"""
Semantic chunking implementation for intelligent document processing.
"""
import re
import uuid
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from models.base import ProcessedChunk, DocumentMetadata, ContentType
from processors.interfaces import SemanticChunkerInterface


@dataclass
class DocumentStructure:
    """Document structure analysis result."""
    headers: List[Tuple[int, str, int]]  # (level, text, position)
    sections: List[Tuple[str, int, int]]  # (title, start, end)
    paragraphs: List[Tuple[int, int]]  # (start, end)
    content_blocks: List[Tuple[str, int, int, ContentType]]  # (content, start, end, type)


class SemanticChunker(SemanticChunkerInterface):
    """
    Semantic chunker that creates intelligent chunks based on document structure.
    
    Features:
    - Analyzes document structure (headers, sections, paragraphs)
    - Adaptive chunk sizing based on content type
    - Preserves hierarchical context
    - Handles mathematical formulas and code blocks
    """
    
    def __init__(self, min_chunk_size: int = 500, max_chunk_size: int = 2000):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
        # Patterns for content type detection
        self.formula_patterns = [
            r'\$[^$]+\$',  # LaTeX inline math
            r'\$\$[^$]+\$\$',  # LaTeX display math
            r'\\begin\{equation\}.*?\\end\{equation\}',  # LaTeX equations
            r'\\begin\{align\}.*?\\end\{align\}',  # LaTeX align
            r'[a-zA-Z]\s*=\s*[^,\n]+',  # Simple equations
            r'∫|∑|∏|√|±|≤|≥|≠|≈|∞',  # Mathematical symbols
        ]
        
        self.code_patterns = [
            r'```[\s\S]*?```',  # Markdown code blocks
            r'`[^`]+`',  # Inline code
            r'def\s+\w+\s*\(',  # Python functions
            r'class\s+\w+\s*[:\(]',  # Python classes
            r'import\s+\w+',  # Import statements
            r'#include\s*<[^>]+>',  # C/C++ includes
        ]
        
        self.header_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headers
            r'^(.+)\n=+$',  # Underlined headers (level 1)
            r'^(.+)\n-+$',  # Underlined headers (level 2)
            r'^\d+\.\s+(.+)$',  # Numbered sections
            r'^[A-Z][A-Z\s]+$',  # ALL CAPS headers
        ]
    
    def chunk_document(self, content: str, metadata: DocumentMetadata) -> List[ProcessedChunk]:
        """
        Chunk document based on semantic structure.
        
        Args:
            content: Document content as string
            metadata: Document metadata
            
        Returns:
            List of processed chunks with hierarchical context
        """
        # Handle empty content
        if not content or not content.strip():
            return []
        
        # Analyze document structure
        structure = self.analyze_structure(content)
        
        # Create chunks based on structure with proper hierarchical context
        chunks = []
        
        # Build hierarchical context from headers
        context_stack = []
        
        for header_level, header_title, header_pos in structure.headers:
            # Update context stack based on header level
            # Remove headers at same or lower level
            context_stack = [ctx for ctx in context_stack if ctx[0] < header_level]
            # Add current header
            context_stack.append((header_level, header_title))
            
            # Find the section for this header
            section_start = header_pos
            section_end = len(content)
            
            # Find end of this section (next header at same or higher level)
            for next_level, _, next_pos in structure.headers:
                if next_pos > header_pos and next_level <= header_level:
                    section_end = next_pos
                    break
            
            section_content = content[section_start:section_end]
            
            # Build hierarchical context from stack
            hierarchical_context = [ctx[1] for ctx in context_stack]
            
            # Create chunks for this section
            section_chunks = self._create_section_chunks(
                section_content, 
                metadata, 
                hierarchical_context.copy(),
                section_start,
                len(content)
            )
            
            chunks.extend(section_chunks)
        
        # If no headers found, fall back to paragraph-based chunking
        if not structure.headers:
            chunks = self._create_paragraph_chunks(content, metadata, structure)
        
        return chunks
    
    def analyze_structure(self, content: str) -> DocumentStructure:
        """
        Analyze document structure to identify headers, sections, and content blocks.
        
        Args:
            content: Document content
            
        Returns:
            DocumentStructure with analyzed components
        """
        headers = self._extract_headers(content)
        sections = self._extract_sections(content, headers)
        paragraphs = self._extract_paragraphs(content)
        content_blocks = self._extract_content_blocks(content)
        
        return DocumentStructure(
            headers=headers,
            sections=sections,
            paragraphs=paragraphs,
            content_blocks=content_blocks
        )
    
    def adaptive_chunk_size(self, content: str, content_type: ContentType) -> int:
        """
        Determine optimal chunk size based on content type.
        
        Args:
            content: Content to analyze
            content_type: Type of content
            
        Returns:
            Optimal chunk size in characters
        """
        base_size = self.min_chunk_size
        
        # Adjust based on content type
        if content_type == ContentType.FORMULA:
            # Mathematical content needs more context
            return min(self.max_chunk_size, base_size * 1.5)
        elif content_type == ContentType.CODE:
            # Code blocks should be kept together when possible
            return min(self.max_chunk_size, base_size * 1.2)
        elif content_type == ContentType.TABLE:
            # Tables need to be preserved as units
            return min(self.max_chunk_size, len(content) + 200)
        elif content_type == ContentType.DIAGRAM:
            # Diagram descriptions need context
            return min(self.max_chunk_size, base_size * 1.3)
        else:
            # Regular text
            return base_size
    
    def _extract_headers(self, content: str) -> List[Tuple[int, str, int]]:
        """Extract headers with their levels and positions."""
        headers = []
        lines = content.split('\n')
        position = 0
        
        for i, line in enumerate(lines):
            line_start = position
            position += len(line) + 1  # +1 for newline
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check each header pattern
            for pattern in self.header_patterns:
                match = re.match(pattern, line.strip(), re.MULTILINE)
                if match:
                    level = self._determine_header_level(line, pattern)
                    text = match.group(1) if match.groups() else line.strip()
                    # Clean up the header text
                    text = text.strip()
                    headers.append((level, text, line_start))
                    break
        
        return headers
    
    def _extract_sections(self, content: str, headers: List[Tuple[int, str, int]]) -> List[Tuple[str, int, int]]:
        """Extract sections based on headers."""
        if not headers:
            # No headers found, treat entire document as one section
            return [("Document", 0, len(content))]
        
        sections = []
        
        for i, (level, title, start_pos) in enumerate(headers):
            # Find end position (start of next header at same or higher level)
            end_pos = len(content)
            
            for j in range(i + 1, len(headers)):
                next_level, _, next_pos = headers[j]
                if next_level <= level:
                    end_pos = next_pos
                    break
            
            sections.append((title, start_pos, end_pos))
        
        return sections
    
    def _extract_paragraphs(self, content: str) -> List[Tuple[int, int]]:
        """Extract paragraph boundaries."""
        paragraphs = []
        lines = content.split('\n')
        current_paragraph_start = 0
        current_position = 0
        in_paragraph = False
        
        for line in lines:
            line_length = len(line)
            
            if line.strip():  # Non-empty line
                if not in_paragraph:
                    current_paragraph_start = current_position
                    in_paragraph = True
            else:  # Empty line
                if in_paragraph:
                    paragraphs.append((current_paragraph_start, current_position))
                    in_paragraph = False
            
            current_position += line_length + 1  # +1 for newline
        
        # Handle last paragraph if document doesn't end with empty line
        if in_paragraph:
            paragraphs.append((current_paragraph_start, current_position))
        
        return paragraphs
    
    def _extract_content_blocks(self, content: str) -> List[Tuple[str, int, int, ContentType]]:
        """Extract and classify content blocks."""
        blocks = []
        
        # Find formula blocks
        for pattern in self.formula_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                blocks.append((
                    match.group(),
                    match.start(),
                    match.end(),
                    ContentType.FORMULA
                ))
        
        # Find code blocks
        for pattern in self.code_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                blocks.append((
                    match.group(),
                    match.start(),
                    match.end(),
                    ContentType.CODE
                ))
        
        # Sort blocks by position
        blocks.sort(key=lambda x: x[1])
        
        return blocks
    
    def _create_section_chunks(self, section_content: str, metadata: DocumentMetadata, 
                             context: List[str], section_start: int, total_length: int) -> List[ProcessedChunk]:
        """Create chunks for a document section."""
        chunks = []
        
        # Determine content type for the section
        content_type = self._classify_section_content(section_content)
        target_size = self.adaptive_chunk_size(section_content, content_type)
        
        # If section is small enough, create single chunk
        if len(section_content) <= target_size:
            chunk = self._create_chunk(
                content=section_content,
                metadata=metadata,
                context=context,
                content_type=content_type,
                position=section_start / total_length
            )
            chunks.append(chunk)
        else:
            # Split section into multiple chunks
            chunks.extend(self._split_section_content(
                section_content, metadata, context, content_type, 
                section_start, total_length, target_size
            ))
        
        return chunks
    
    def _create_paragraph_chunks(self, content: str, metadata: DocumentMetadata, 
                               structure: DocumentStructure) -> List[ProcessedChunk]:
        """Create chunks based on paragraph boundaries when no clear sections exist."""
        chunks = []
        
        # If no paragraphs found or content is very large, use sentence-based splitting
        if not structure.paragraphs or len(content) > self.max_chunk_size:
            return self._create_sentence_based_chunks(content, metadata)
        
        current_chunk_content = ""
        current_chunk_start = 0
        
        for para_start, para_end in structure.paragraphs:
            paragraph = content[para_start:para_end]
            
            # Check if adding this paragraph would exceed chunk size
            if (len(current_chunk_content) + len(paragraph) > self.max_chunk_size 
                and current_chunk_content):
                
                # Create chunk with current content
                chunk = self._create_chunk(
                    content=current_chunk_content.strip(),
                    metadata=metadata,
                    context=["Document"],
                    content_type=self._classify_section_content(current_chunk_content),
                    position=current_chunk_start / len(content)
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk_content = paragraph
                current_chunk_start = para_start
            else:
                current_chunk_content += paragraph
                if not current_chunk_content.strip():
                    current_chunk_start = para_start
        
        # Add final chunk if there's remaining content
        if current_chunk_content.strip():
            chunk = self._create_chunk(
                content=current_chunk_content.strip(),
                metadata=metadata,
                context=["Document"],
                content_type=self._classify_section_content(current_chunk_content),
                position=current_chunk_start / len(content)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_sentence_based_chunks(self, content: str, metadata: DocumentMetadata) -> List[ProcessedChunk]:
        """Create chunks based on sentence boundaries for large unstructured content."""
        chunks = []
        sentences = self._split_into_sentences(content)
        
        current_chunk = ""
        chunk_start_pos = 0
        
        for sentence in sentences:
            # Check if adding this sentence would exceed target size
            if len(current_chunk) + len(sentence) > self.max_chunk_size and current_chunk:
                # Create chunk with current content
                chunk = self._create_chunk(
                    content=current_chunk.strip(),
                    metadata=metadata,
                    context=["Document"],
                    content_type=self._classify_section_content(current_chunk),
                    position=chunk_start_pos / len(content)
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk = sentence
                chunk_start_pos += len(current_chunk)
            else:
                current_chunk += sentence
        
        # Add final chunk if there's remaining content
        if current_chunk.strip():
            chunk = self._create_chunk(
                content=current_chunk.strip(),
                metadata=metadata,
                context=["Document"],
                content_type=self._classify_section_content(current_chunk),
                position=chunk_start_pos / len(content)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(self, content: str, metadata: DocumentMetadata, context: List[str],
                     content_type: ContentType, position: float, page_number: int = 1) -> ProcessedChunk:
        """Create a ProcessedChunk object."""
        return ProcessedChunk(
            chunk_id=str(uuid.uuid4()),
            document_id=metadata.document_id,
            content=content,
            content_type=content_type,
            hierarchical_context=context,
            page_number=page_number,
            position_in_document=position,
            metadata={
                "chunk_size": len(content),
                "content_classification": content_type.value,
                "context_depth": len(context)
            }
        )
    
    def _classify_section_content(self, content: str) -> ContentType:
        """Classify the primary content type of a section."""
        if not content:
            return ContentType.TEXT
            
        # Count different content types
        formula_matches = sum(len(re.findall(pattern, content, re.DOTALL)) for pattern in self.formula_patterns)
        code_matches = sum(len(re.findall(pattern, content, re.DOTALL)) for pattern in self.code_patterns)
        
        # Calculate character coverage for formulas and code
        formula_chars = 0
        for pattern in self.formula_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                formula_chars += len(match.group())
        
        code_chars = 0
        for pattern in self.code_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                code_chars += len(match.group())
        
        total_length = len(content)
        
        # Use character coverage instead of match count for better classification
        if formula_chars > 0 and formula_chars / total_length > 0.15:
            return ContentType.FORMULA
        elif code_chars > 0 and code_chars / total_length > 0.15:
            return ContentType.CODE
        else:
            return ContentType.TEXT
    
    def _split_section_content(self, content: str, metadata: DocumentMetadata, context: List[str],
                             content_type: ContentType, section_start: int, total_length: int,
                             target_size: int) -> List[ProcessedChunk]:
        """Split section content into appropriately sized chunks."""
        chunks = []
        sentences = self._split_into_sentences(content)
        
        current_chunk = ""
        chunk_start_pos = 0
        
        for sentence in sentences:
            # Check if adding this sentence would exceed target size
            if len(current_chunk) + len(sentence) > target_size and current_chunk:
                # Create chunk with current content
                chunk = self._create_chunk(
                    content=current_chunk.strip(),
                    metadata=metadata,
                    context=context,
                    content_type=content_type,
                    position=(section_start + chunk_start_pos) / total_length
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk = sentence
                chunk_start_pos += len(current_chunk)
            else:
                current_chunk += sentence
        
        # Add final chunk if there's remaining content
        if current_chunk.strip():
            chunk = self._create_chunk(
                content=current_chunk.strip(),
                metadata=metadata,
                context=context,
                content_type=content_type,
                position=(section_start + chunk_start_pos) / total_length
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences while preserving structure."""
        # Simple sentence splitting that preserves formulas and code
        sentences = []
        current_sentence = ""
        
        i = 0
        while i < len(text):
            char = text[i]
            current_sentence += char
            
            # Check for sentence endings
            if char in '.!?':
                # Look ahead to see if this is really a sentence end
                if i + 1 < len(text) and text[i + 1].isspace():
                    # Check if next non-space character is uppercase (new sentence)
                    j = i + 1
                    while j < len(text) and text[j].isspace():
                        j += 1
                    
                    if j < len(text) and (text[j].isupper() or text[j] in '0123456789'):
                        sentences.append(current_sentence)
                        current_sentence = ""
            
            i += 1
        
        # Add remaining content
        if current_sentence.strip():
            sentences.append(current_sentence)
        
        return sentences
    
    def _determine_header_level(self, line: str, pattern: str) -> int:
        """Determine header level based on pattern and content."""
        if pattern.startswith('^#{'):
            # Markdown headers - count #
            return len(re.match(r'^#+', line.strip()).group())
        elif '=+$' in pattern:
            return 1  # Underlined with =
        elif '-+$' in pattern:
            return 2  # Underlined with -
        elif r'^\d+\.' in pattern:
            # Numbered sections - count dots
            match = re.match(r'^(\d+\.)+', line.strip())
            return len(match.group().split('.')) - 1 if match else 1
        else:
            return 1  # Default level
    
    def _get_header_level(self, header_text: str) -> int:
        """Get header level from header text."""
        # Simple heuristic based on common patterns
        if re.match(r'^\d+\.\s', header_text):
            return 1
        elif re.match(r'^\d+\.\d+\s', header_text):
            return 2
        elif re.match(r'^\d+\.\d+\.\d+\s', header_text):
            return 3
        else:
            return 1
    
    def _update_context(self, current_context: List[str], new_header: str, level: int) -> List[str]:
        """Update hierarchical context based on new header."""
        # Ensure level is at least 1
        level = max(1, level)
        
        # Trim context to appropriate level (keep parent levels)
        if level == 1:
            context = []
        else:
            context = current_context[:level-1]
        
        # Add new header
        context.append(new_header)
        
        return context