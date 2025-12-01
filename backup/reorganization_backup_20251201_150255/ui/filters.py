"""
Filtering and Search Enhancement Components
Implements document type, course module, and difficulty level filters
"""

import streamlit as st
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import json


class DocumentType(Enum):
    """Document type enumeration"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    SLIDES = "slides"
    EXERCISES = "exercises"
    SYLLABUS = "syllabus"


class DifficultyLevel(Enum):
    """Difficulty level enumeration"""
    BEGINNER = "débutant"
    INTERMEDIATE = "intermédiaire"
    ADVANCED = "avancé"
    EXPERT = "expert"


class CourseModule(Enum):
    """Course module enumeration"""
    NETWORKS = "Réseaux et Télécommunications"
    SECURITY = "Sécurité Informatique"
    WEB_DEV = "Développement Web"
    DATABASES = "Bases de Données"
    SYSTEMS = "Systèmes d'Exploitation"
    PROGRAMMING = "Programmation"
    AI = "Intelligence Artificielle"
    MATHEMATICS = "Mathématiques Appliquées"
    PROJECT_MGMT = "Gestion de Projet"


class SearchFilters:
    """Search filters management"""
    
    def __init__(self):
        self.active_filters = {}
    
    def render_document_type_filter(self) -> List[str]:
        """Render document type filter"""
        st.markdown("**📄 Type de document**")
        
        selected_types = []
        doc_types = [
            ("PDF", "📕 Documents PDF"),
            ("Slides", "📊 Présentations"),
            ("Exercises", "📝 Exercices"),
            ("Syllabus", "📋 Syllabus"),
            ("Notes", "📓 Notes de cours")
        ]
        
        cols = st.columns(len(doc_types))
        for i, (doc_type, label) in enumerate(doc_types):
            with cols[i]:
                if st.checkbox(label, key=f"doc_type_{doc_type.lower()}"):
                    selected_types.append(doc_type.lower())
        
        return selected_types
    
    def render_course_module_filter(self) -> List[str]:
        """Render course module filter"""
        st.markdown("**📚 Module de cours**")
        
        modules = [module.value for module in CourseModule]
        selected_modules = st.multiselect(
            "Sélectionnez les modules",
            modules,
            key="course_modules_filter",
            help="Filtrer par module de cours spécifique"
        )
        
        return selected_modules
    
    def render_difficulty_filter(self) -> List[str]:
        """Render difficulty level filter"""
        st.markdown("**🎯 Niveau de difficulté**")
        
        difficulty_levels = [level.value for level in DifficultyLevel]
        selected_levels = st.multiselect(
            "Sélectionnez les niveaux",
            difficulty_levels,
            key="difficulty_filter",
            help="Filtrer par niveau de difficulté"
        )
        
        return selected_levels
    
    def render_date_filter(self) -> Optional[Tuple[str, str]]:
        """Render date range filter"""
        st.markdown("**📅 Période**")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Date de début", key="start_date_filter")
        with col2:
            end_date = st.date_input("Date de fin", key="end_date_filter")
        
        if start_date and end_date:
            return (start_date.isoformat(), end_date.isoformat())
        return None
    
    def get_active_filters(self) -> Dict[str, Any]:
        """Get all active filters"""
        filters = {}
        
        # Document types
        doc_types = self.render_document_type_filter()
        if doc_types:
            filters["document_types"] = doc_types
        
        # Course modules
        modules = self.render_course_module_filter()
        if modules:
            filters["course_modules"] = modules
        
        # Difficulty levels
        difficulty = self.render_difficulty_filter()
        if difficulty:
            filters["difficulty_levels"] = difficulty
        
        # Date range
        date_range = self.render_date_filter()
        if date_range:
            filters["date_range"] = date_range
        
        return filters
    
    def clear_filters(self) -> None:
        """Clear all active filters"""
        filter_keys = [
            "doc_type_pdf", "doc_type_slides", "doc_type_exercises", 
            "doc_type_syllabus", "doc_type_notes",
            "course_modules_filter", "difficulty_filter",
            "start_date_filter", "end_date_filter"
        ]
        
        for key in filter_keys:
            if key in st.session_state:
                del st.session_state[key]


class ContextualHelp:
    """Contextual help system with example queries"""
    
    def __init__(self):
        self.example_queries = self._load_example_queries()
    
    def _load_example_queries(self) -> Dict[str, List[str]]:
        """Load example queries by category"""
        return {
            "Réseaux": [
                "Expliquez le modèle OSI et ses 7 couches",
                "Quelle est la différence entre TCP et UDP ?",
                "Comment fonctionne le protocole DHCP ?",
                "Qu'est-ce qu'un VLAN et comment le configurer ?"
            ],
            "Sécurité": [
                "Quels sont les types d'attaques par déni de service ?",
                "Comment fonctionne le chiffrement RSA ?",
                "Expliquez les principes de l'authentification multi-facteurs",
                "Qu'est-ce qu'un firewall et comment le configurer ?"
            ],
            "Programmation": [
                "Expliquez les concepts de la programmation orientée objet",
                "Quelle est la différence entre une liste et un tuple en Python ?",
                "Comment implémenter un algorithme de tri rapide ?",
                "Qu'est-ce que la récursivité et donnez un exemple"
            ],
            "Bases de données": [
                "Expliquez les formes normales en base de données",
                "Quelle est la différence entre INNER JOIN et LEFT JOIN ?",
                "Comment optimiser une requête SQL lente ?",
                "Qu'est-ce qu'une transaction ACID ?"
            ],
            "Intelligence Artificielle": [
                "Expliquez le fonctionnement des réseaux de neurones",
                "Quelle est la différence entre apprentissage supervisé et non supervisé ?",
                "Comment fonctionne l'algorithme de rétropropagation ?",
                "Qu'est-ce que l'overfitting et comment l'éviter ?"
            ]
        }
    
    def render_help_panel(self) -> None:
        """Render contextual help panel"""
        with st.expander("💡 Aide et exemples de questions", expanded=False):
            st.markdown("### Comment poser une bonne question ?")
            
            st.markdown("""
            **Conseils pour obtenir de meilleures réponses :**
            - Soyez spécifique dans votre question
            - Mentionnez le contexte ou le module de cours
            - Utilisez des mots-clés techniques appropriés
            - Demandez des exemples concrets si nécessaire
            """)
            
            st.markdown("### 📝 Exemples de questions par domaine")
            
            for category, queries in self.example_queries.items():
                with st.expander(f"📚 {category}", expanded=False):
                    for i, query in enumerate(queries):
                        if st.button(f"💬 {query}", key=f"example_{category}_{i}"):
                            st.session_state["main_query"] = query
                            from utils.streamlit_compat import safe_rerun
                            safe_rerun()
    
    def render_query_suggestions(self, current_query: str) -> List[str]:
        """Render query improvement suggestions"""
        if not current_query or len(current_query) < 10:
            return []
        
        suggestions = []
        
        # Analyze query and provide suggestions
        if "?" not in current_query:
            suggestions.append("💡 Essayez de formuler votre demande sous forme de question")
        
        if len(current_query.split()) < 3:
            suggestions.append("💡 Ajoutez plus de détails pour une réponse plus précise")
        
        # Check for technical terms
        technical_terms = ["protocole", "algorithme", "fonction", "méthode", "classe", "réseau"]
        if not any(term in current_query.lower() for term in technical_terms):
            suggestions.append("💡 Utilisez des termes techniques spécifiques si applicable")
        
        if suggestions:
            st.markdown("**Suggestions pour améliorer votre question :**")
            for suggestion in suggestions:
                st.info(suggestion)
        
        return suggestions


class SearchEnhancementManager:
    """Manager for search enhancement features"""
    
    def __init__(self):
        self.filters = SearchFilters()
        self.help_system = ContextualHelp()
    
    def render_filter_sidebar(self) -> Dict[str, Any]:
        """Render filter sidebar"""
        with st.sidebar:
            st.markdown("## 🔍 Filtres de recherche")
            
            # Clear filters button
            if st.button("🗑️ Effacer tous les filtres", key="clear_filters"):
                self.filters.clear_filters()
                from utils.streamlit_compat import safe_rerun
                safe_rerun()
            
            st.markdown("---")
            
            # Get active filters
            active_filters = self.filters.get_active_filters()
            
            # Show active filters count
            if active_filters:
                filter_count = sum(len(v) if isinstance(v, list) else 1 for v in active_filters.values())
                st.success(f"✅ {filter_count} filtre(s) actif(s)")
            
            return active_filters
    
    def render_search_enhancements(self, query: str) -> None:
        """Render search enhancement features"""
        # Query suggestions
        self.help_system.render_query_suggestions(query)
        
        # Help panel
        self.help_system.render_help_panel()
    
    def apply_filters_to_query(self, query: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filters to search query"""
        enhanced_query = {
            "query": query,
            "filters": filters,
            "metadata_filters": {}
        }
        
        # Convert filters to metadata filters
        if "document_types" in filters:
            enhanced_query["metadata_filters"]["document_type"] = {"$in": filters["document_types"]}
        
        if "course_modules" in filters:
            enhanced_query["metadata_filters"]["course_module"] = {"$in": filters["course_modules"]}
        
        if "difficulty_levels" in filters:
            enhanced_query["metadata_filters"]["difficulty_level"] = {"$in": filters["difficulty_levels"]}
        
        if "date_range" in filters:
            start_date, end_date = filters["date_range"]
            enhanced_query["metadata_filters"]["created_date"] = {
                "$gte": start_date,
                "$lte": end_date
            }
        
        return enhanced_query