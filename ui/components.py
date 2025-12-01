"""
Advanced UI Components for the RAG System
Implements auto-complete, formula rendering, and expandable sections
"""

import streamlit as st
import re
from typing import List, Dict, Any, Optional
import json
from pathlib import Path


class AutoCompleteComponent:
    """Auto-complete functionality using course content index"""
    
    def __init__(self, content_index: Optional[Dict[str, List[str]]] = None):
        self.content_index = content_index or self._load_content_index()
    
    def _load_content_index(self) -> Dict[str, List[str]]:
        """Load course content index for auto-complete suggestions"""
        # Default suggestions based on common course topics
        return {
            "topics": [
                "réseaux", "télécommunications", "protocoles", "TCP/IP", "OSI",
                "sécurité", "cryptographie", "authentification", "firewall",
                "programmation", "algorithmes", "structures de données",
                "bases de données", "SQL", "NoSQL", "modélisation",
                "systèmes", "linux", "windows", "virtualisation",
                "web", "HTML", "CSS", "JavaScript", "frameworks",
                "mobile", "Android", "iOS", "développement",
                "intelligence artificielle", "machine learning", "deep learning",
                "mathématiques", "statistiques", "probabilités", "analyse"
            ],
            "commands": [
                "Expliquez", "Définissez", "Comparez", "Analysez", "Décrivez",
                "Quelles sont", "Comment", "Pourquoi", "Où", "Quand",
                "Donnez un exemple", "Listez", "Résumez", "Calculez"
            ],
            "course_modules": [
                "Réseaux et Télécommunications", "Sécurité Informatique",
                "Développement Web", "Bases de Données", "Systèmes d'Exploitation",
                "Programmation Orientée Objet", "Intelligence Artificielle",
                "Mathématiques Appliquées", "Gestion de Projet"
            ]
        }
    
    def get_suggestions(self, query: str, max_suggestions: int = 5) -> List[str]:
        """Get auto-complete suggestions based on partial query"""
        if not query or len(query) < 2:
            return []
        
        query_lower = query.lower()
        suggestions = []
        
        # Search in all categories
        for category, items in self.content_index.items():
            for item in items:
                if query_lower in item.lower() and item not in suggestions:
                    suggestions.append(item)
                    if len(suggestions) >= max_suggestions:
                        break
            if len(suggestions) >= max_suggestions:
                break
        
        return suggestions[:max_suggestions]
    
    def render_autocomplete_input(self, key: str = "query_input", 
                                placeholder: str = "Posez votre question...") -> str:
        """Render auto-complete input field"""
        # Create a text input with suggestions
        query = st.text_input(
            "Question",
            placeholder=placeholder,
            key=key,
            help="Commencez à taper pour voir les suggestions"
        )
        
        if query and len(query) >= 2:
            suggestions = self.get_suggestions(query)
            if suggestions:
                st.write("**Suggestions:**")
                cols = st.columns(min(len(suggestions), 3))
                for i, suggestion in enumerate(suggestions):
                    with cols[i % 3]:
                        if st.button(f"📝 {suggestion}", key=f"suggestion_{i}_{key}"):
                            st.session_state[key] = suggestion
                            st.rerun()
        
        return query


class FormulaRenderer:
    """Mathematical formula and code snippet rendering"""
    
    @staticmethod
    def render_math_formula(text: str) -> str:
        """Render mathematical formulas using LaTeX"""
        # Find LaTeX patterns and render them
        latex_pattern = r'\$\$([^$]+)\$\$|\$([^$]+)\$'
        
        def replace_latex(match):
            formula = match.group(1) or match.group(2)
            return f"$$\n{formula}\n$$"
        
        return re.sub(latex_pattern, replace_latex, text)
    
    @staticmethod
    def render_code_snippet(code: str, language: str = "python") -> None:
        """Render code snippets with syntax highlighting"""
        st.code(code, language=language)
    
    @staticmethod
    def detect_and_render_content(text: str) -> None:
        """Detect and render mathematical formulas and code snippets"""
        # Split text into sections
        sections = text.split('\n\n')
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # Check if section contains code (starts with common code indicators)
            code_indicators = ['def ', 'class ', 'import ', 'from ', '```', 'function', 'var ', 'let ', 'const ']
            if any(indicator in section for indicator in code_indicators):
                # Extract language if specified
                if section.startswith('```'):
                    lines = section.split('\n')
                    if len(lines) > 0:
                        lang_line = lines[0].replace('```', '').strip()
                        language = lang_line if lang_line else 'text'
                        code_content = '\n'.join(lines[1:]).replace('```', '')
                        FormulaRenderer.render_code_snippet(code_content, language)
                    continue
                else:
                    FormulaRenderer.render_code_snippet(section)
                    continue
            
            # Check if section contains mathematical formulas
            if '$' in section or any(math_term in section.lower() for math_term in 
                                   ['équation', 'formule', '=', '∑', '∫', 'θ', 'α', 'β', 'γ']):
                rendered_text = FormulaRenderer.render_math_formula(section)
                st.markdown(rendered_text)
            else:
                st.markdown(section)


class ExpandableResponse:
    """Expandable response sections with table of contents"""
    
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.sections = self._parse_sections()
    
    def _parse_sections(self) -> List[Dict[str, Any]]:
        """Parse response into sections based on headers and content"""
        sections = []
        lines = self.response_text.split('\n')
        current_section = {"title": "Introduction", "content": "", "level": 0}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect headers (markdown style)
            if line.startswith('#'):
                if current_section["content"].strip():
                    sections.append(current_section)
                
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                current_section = {"title": title, "content": "", "level": level}
            else:
                current_section["content"] += line + "\n"
        
        # Add the last section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections
    
    def render_table_of_contents(self) -> None:
        """Render table of contents for the response"""
        if len(self.sections) <= 1:
            return
        
        st.markdown("### 📋 Table des matières")
        for i, section in enumerate(self.sections):
            indent = "  " * section["level"]
            if st.button(f"{indent}📖 {section['title']}", key=f"toc_{i}"):
                st.session_state[f"expand_section_{i}"] = True
    
    def render_expandable_sections(self) -> None:
        """Render response as expandable sections"""
        if len(self.sections) <= 1:
            # Single section, render normally
            FormulaRenderer.detect_and_render_content(self.response_text)
            return
        
        # Multiple sections, render as expandable
        for i, section in enumerate(self.sections):
            expanded = st.session_state.get(f"expand_section_{i}", i == 0)  # First section expanded by default
            
            with st.expander(f"📖 {section['title']}", expanded=expanded):
                FormulaRenderer.detect_and_render_content(section["content"])


class UIComponentManager:
    """Manager for all UI components"""
    
    def __init__(self):
        self.autocomplete = AutoCompleteComponent()
        self.formula_renderer = FormulaRenderer()
    
    def render_enhanced_input(self, key: str = "main_query") -> str:
        """Render enhanced input with auto-complete"""
        return self.autocomplete.render_autocomplete_input(key)
    
    def render_enhanced_response(self, response_text: str) -> None:
        """Render enhanced response with formulas and expandable sections"""
        expandable_response = ExpandableResponse(response_text)
        
        # Render table of contents if multiple sections
        expandable_response.render_table_of_contents()
        
        # Render expandable sections
        expandable_response.render_expandable_sections()
    
    def add_response_feedback(self, response_id: str) -> Optional[Dict[str, Any]]:
        """Add feedback collection for responses"""
        st.markdown("---")
        st.markdown("**Cette réponse vous a-t-elle été utile ?**")
        
        col1, col2, col3 = st.columns(3)
        
        feedback = None
        with col1:
            if st.button("👍 Utile", key=f"helpful_{response_id}"):
                feedback = {"rating": "helpful", "response_id": response_id}
        
        with col2:
            if st.button("👎 Pas utile", key=f"not_helpful_{response_id}"):
                feedback = {"rating": "not_helpful", "response_id": response_id}
        
        with col3:
            if st.button("🤔 Partiellement", key=f"partial_{response_id}"):
                feedback = {"rating": "partial", "response_id": response_id}
        
        return feedback