"""
Response Manager for generating high-quality responses with citations and confidence scoring.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from src.models.base import Response, RetrievalResult, ConversationContext, ProcessedChunk
from .interfaces import ResponseManagerInterface
from .synthesis_manager import SynthesisManager
from config.settings import get_settings


logger = logging.getLogger(__name__)


class ResponseManager(ResponseManagerInterface):
    """
    Manages response generation with advanced citation and confidence scoring.
    """
    
    def __init__(self, llm_model: str = None):
        """Initialize the response manager."""
        self.settings = get_settings()
        self.llm_model = llm_model or self.settings.model.ollama_model
        self.llm = ChatOllama(model=self.llm_model)
        
        # Initialize synthesis manager
        self.synthesis_manager = SynthesisManager()
        
        # Enhanced prompt templates
        self.citation_prompt = self._create_citation_prompt()
        self.synthesis_prompt = self._create_synthesis_prompt()
        
        # Citation patterns for parsing
        self.citation_pattern = re.compile(r'\[(\d+)\]')
        
    def _create_citation_prompt(self) -> ChatPromptTemplate:
        """Create enhanced prompt template with citation requirements."""
        template = """Tu es un assistant éducatif expert pour les étudiants en Smart ICT à l'INPT.

INSTRUCTIONS IMPORTANTES:
1. Réponds UNIQUEMENT en te basant sur le contexte fourni ci-dessous
2. CITE TOUJOURS tes sources en utilisant le format [numéro] après chaque information
3. Si l'information n'est pas dans le contexte, dis clairement que tu ne sais pas
4. Organise ta réponse de manière claire et structurée
5. Indique ton niveau de confiance si l'information est incertaine

CONTEXTE AVEC SOURCES:
{context_with_sources}

CONVERSATION PRÉCÉDENTE (si applicable):
{conversation_context}

QUESTION: {input}

RÉPONSE (avec citations obligatoires):"""
        
        return ChatPromptTemplate.from_template(template)
    
    def _create_synthesis_prompt(self) -> ChatPromptTemplate:
        """Create prompt template for multi-source synthesis."""
        template = """Tu es un assistant éducatif expert qui doit synthétiser des informations provenant de plusieurs sources.

INSTRUCTIONS:
1. Compare et synthétise les informations des différentes sources
2. Identifie les points de convergence et de divergence
3. Signale explicitement les conflits entre sources
4. Hiérarchise les informations selon leur fiabilité
5. Cite toutes les sources utilisées

SOURCES À SYNTHÉTISER:
{sources_content}

QUESTION: {input}

SYNTHÈSE COMPLÈTE (avec analyse des sources):"""
        
        return ChatPromptTemplate.from_template(template)
    
    def generate_response(self, query: str, context: List[RetrievalResult], 
                         conversation: Optional[ConversationContext] = None) -> Response:
        """
        Generate response from query and context with citations.
        
        Args:
            query: User query
            context: Retrieved context chunks
            conversation: Optional conversation context
            
        Returns:
            Response with citations and confidence score
        """
        try:
            # Prepare context with source numbering
            context_with_sources = self._prepare_context_with_sources(context)
            
            # Prepare conversation context
            conversation_text = ""
            if conversation and conversation.recent_messages:
                conversation_text = self._format_conversation_context(conversation)
            
            # Generate response using LLM
            response_content = self._generate_llm_response(
                query, context_with_sources, conversation_text
            )
            
            # Extract and validate citations
            citations = self._extract_citations(response_content, context)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(response_content, context)
            
            # Create response object
            response = Response(
                content=response_content,
                sources=context,
                confidence=confidence,
                citations=citations,
                generation_metadata={
                    "timestamp": datetime.now().isoformat(),
                    "model": self.llm_model,
                    "num_sources": len(context),
                    "query_length": len(query),
                    "response_length": len(response_content)
                }
            )
            
            logger.info(f"Generated response with {len(citations)} citations, confidence: {confidence:.2f}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def _prepare_context_with_sources(self, context: List[RetrievalResult]) -> str:
        """Prepare context with numbered sources for citation."""
        context_parts = []
        
        for i, result in enumerate(context, 1):
            chunk = result.chunk
            source_info = f"[{i}] Source: {chunk.metadata.get('title', 'Document')} - Page {chunk.page_number}"
            
            # Add hierarchical context if available
            if chunk.hierarchical_context:
                context_path = " > ".join(chunk.hierarchical_context)
                source_info += f" - Section: {context_path}"
            
            context_parts.append(f"{source_info}\nContenu: {chunk.content}\n")
        
        return "\n".join(context_parts)
    
    def _format_conversation_context(self, conversation: ConversationContext) -> str:
        """Format conversation context for prompt."""
        if not conversation.recent_messages:
            return ""
        
        context_parts = []
        for msg in conversation.recent_messages[-3:]:  # Last 3 messages
            role = "Étudiant" if msg.role == "user" else "Assistant"
            context_parts.append(f"{role}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def _generate_llm_response(self, query: str, context_with_sources: str, 
                              conversation_text: str) -> str:
        """Generate response using LLM with citation prompt."""
        try:
            # Create the prompt
            prompt_input = {
                "input": query,
                "context_with_sources": context_with_sources,
                "conversation_context": conversation_text
            }
            
            # Generate response
            chain = self.citation_prompt | self.llm
            response = chain.invoke(prompt_input)
            
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            logger.error(f"Error in LLM response generation: {e}")
            raise
    
    def _extract_citations(self, response_content: str, context: List[RetrievalResult]) -> List[str]:
        """Extract and validate citations from response."""
        citations = []
        citation_matches = self.citation_pattern.findall(response_content)
        
        for citation_num in set(citation_matches):
            try:
                idx = int(citation_num) - 1
                if 0 <= idx < len(context):
                    chunk = context[idx].chunk
                    citation = self._format_citation(chunk, int(citation_num))
                    citations.append(citation)
            except (ValueError, IndexError):
                logger.warning(f"Invalid citation number: {citation_num}")
        
        return citations
    
    def _format_citation(self, chunk: ProcessedChunk, citation_num: int) -> str:
        """Format a single citation."""
        title = chunk.metadata.get('title', 'Document')
        page = chunk.page_number
        
        citation = f"[{citation_num}] {title}, page {page}"
        
        # Add section information if available
        if chunk.hierarchical_context:
            section = " > ".join(chunk.hierarchical_context)
            citation += f", section: {section}"
        
        return citation
    
    def _calculate_confidence(self, response_content: str, context: List[RetrievalResult]) -> float:
        """Calculate confidence score based on source relevance and response quality."""
        try:
            # Base confidence from source scores
            if not context:
                return 0.0
            
            source_confidence = sum(result.score for result in context) / len(context)
            
            # Citation coverage (how many sources are cited)
            citations_found = len(set(self.citation_pattern.findall(response_content)))
            citation_coverage = min(citations_found / len(context), 1.0)
            
            # Response length factor (very short responses might be incomplete)
            length_factor = min(len(response_content) / 200, 1.0)  # Normalize to 200 chars
            
            # Uncertainty indicators (reduce confidence if present)
            uncertainty_phrases = [
                "je ne sais pas", "incertain", "peut-être", "probablement",
                "il semble que", "d'après", "selon"
            ]
            uncertainty_penalty = sum(
                1 for phrase in uncertainty_phrases 
                if phrase.lower() in response_content.lower()
            ) * 0.1
            
            # Calculate final confidence
            confidence = (
                source_confidence * 0.4 +
                citation_coverage * 0.3 +
                length_factor * 0.2 +
                0.1  # Base confidence
            ) - uncertainty_penalty
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5  # Default moderate confidence
    
    def add_citations(self, response: str, sources: List[RetrievalResult]) -> str:
        """Add citations to response if not already present."""
        # Check if citations are already present
        if self.citation_pattern.search(response):
            return response
        
        # Add citations at the end if none found
        citations = []
        for i, result in enumerate(sources, 1):
            citation = self._format_citation(result.chunk, i)
            citations.append(citation)
        
        if citations:
            response += "\n\nSources:\n" + "\n".join(citations)
        
        return response
    
    def assess_confidence(self, response: str, sources: List[RetrievalResult]) -> float:
        """Assess confidence in response."""
        return self._calculate_confidence(response, sources)
    
    def synthesize_sources(self, sources: List[RetrievalResult]) -> str:
        """Synthesize information from multiple sources using advanced synthesis manager."""
        if not sources:
            return ""
        
        try:
            # Use the advanced synthesis manager
            synthesis_result = self.synthesis_manager.synthesize_sources(sources)
            
            # Format the result for display
            formatted_synthesis = self._format_synthesis_result(synthesis_result)
            
            return formatted_synthesis
            
        except Exception as e:
            logger.error(f"Error in source synthesis: {e}")
            return "Erreur lors de la synthèse des sources."
    
    def _group_sources_by_document(self, sources: List[RetrievalResult]) -> Dict[str, List[RetrievalResult]]:
        """Group sources by document for conflict detection."""
        groups = {}
        for source in sources:
            doc_id = source.chunk.document_id
            if doc_id not in groups:
                groups[doc_id] = []
            groups[doc_id].append(source)
        return groups
    
    def _prepare_sources_for_synthesis(self, source_groups: Dict[str, List[RetrievalResult]]) -> str:
        """Prepare sources content for synthesis prompt."""
        synthesis_parts = []
        
        for doc_id, sources in source_groups.items():
            doc_title = sources[0].chunk.metadata.get('title', f'Document {doc_id}')
            synthesis_parts.append(f"\n=== {doc_title} ===")
            
            for i, source in enumerate(sources, 1):
                chunk = source.chunk
                page_info = f"Page {chunk.page_number}"
                if chunk.hierarchical_context:
                    section = " > ".join(chunk.hierarchical_context)
                    page_info += f", Section: {section}"
                
                synthesis_parts.append(f"\nExtrait {i} ({page_info}):")
                synthesis_parts.append(chunk.content)
        
        return "\n".join(synthesis_parts)
    
    def _format_synthesis_result(self, synthesis_result) -> str:
        """Format synthesis result for display."""
        from .synthesis_manager import SynthesisResult
        
        if not isinstance(synthesis_result, SynthesisResult):
            return str(synthesis_result)
        
        formatted_parts = []
        
        # Main synthesized content
        formatted_parts.append(synthesis_result.synthesized_content)
        
        # Add reliability information if available
        if synthesis_result.source_reliability:
            formatted_parts.append("\n## 📊 Fiabilité des sources")
            for reliability in synthesis_result.source_reliability:
                formatted_parts.append(
                    f"- Source {reliability.source_id}: {reliability.reliability_score:.2f}/1.0"
                )
        
        # Add conflict information if any
        if synthesis_result.detected_conflicts:
            formatted_parts.append("\n## ⚠️ Conflits détectés")
            for conflict in synthesis_result.detected_conflicts:
                formatted_parts.append(f"- {conflict.description}")
        
        # Add methodology notes
        if synthesis_result.methodology_notes:
            formatted_parts.append(f"\n## 📋 Méthodologie")
            formatted_parts.append(synthesis_result.methodology_notes)
        
        # Add confidence score
        formatted_parts.append(
            f"\n**Confiance de la synthèse: {synthesis_result.synthesis_confidence:.2f}/1.0**"
        )
        
        return "\n".join(formatted_parts)