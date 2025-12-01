"""
Demo script for UI Enhancements
Demonstrates advanced UI components, filtering, and search enhancements
"""

import streamlit as st
import sys
import os
from datetime import datetime, date

# Add the project root to the path (parent directory of demos)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.components import UIComponentManager, AutoCompleteComponent, FormulaRenderer, ExpandableResponse
from src.ui.filters import SearchEnhancementManager, SearchFilters, ContextualHelp


def demo_autocomplete():
    """Demo auto-complete functionality"""
    st.header("🔍 Auto-Complete Demo")
    
    autocomplete = AutoCompleteComponent()
    
    st.markdown("### Test Auto-Complete Suggestions")
    test_queries = ["réseau", "sécurité", "programmation", "base", "intelligence"]
    
    for query in test_queries:
        suggestions = autocomplete.get_suggestions(query, max_suggestions=3)
        if suggestions:
            st.write(f"**Query: '{query}'** → Suggestions: {', '.join(suggestions)}")
    
    st.markdown("### Interactive Auto-Complete")
    query = st.text_input("Type to see suggestions:", key="demo_autocomplete")
    
    if query and len(query) >= 2:
        suggestions = autocomplete.get_suggestions(query)
        if suggestions:
            st.write("**Suggestions:**")
            for i, suggestion in enumerate(suggestions[:5]):
                st.write(f"• {suggestion}")


def demo_formula_rendering():
    """Demo mathematical formula and code rendering"""
    st.header("📐 Formula and Code Rendering Demo")
    
    st.markdown("### Mathematical Formulas")
    
    sample_formulas = [
        "The quadratic formula: $x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$",
        "Euler's identity: $e^{i\\pi} + 1 = 0$",
        "Shannon's entropy: $$H(X) = -\\sum_{i=1}^{n} P(x_i) \\log_2 P(x_i)$$"
    ]
    
    for formula in sample_formulas:
        st.markdown("**Original:**")
        st.code(formula)
        st.markdown("**Rendered:**")
        rendered = FormulaRenderer.render_math_formula(formula)
        st.markdown(rendered)
        st.markdown("---")
    
    st.markdown("### Code Snippets")
    
    sample_code = """```python
def dijkstra(graph, start):
    distances = {node: float('infinity') for node in graph}
    distances[start] = 0
    visited = set()
    
    while len(visited) < len(graph):
        current = min((node for node in graph if node not in visited), 
                     key=lambda x: distances[x])
        visited.add(current)
        
        for neighbor, weight in graph[current].items():
            distances[neighbor] = min(distances[neighbor], 
                                    distances[current] + weight)
    
    return distances
```"""
    
    st.markdown("**Code Example:**")
    FormulaRenderer.detect_and_render_content(sample_code)


def demo_expandable_response():
    """Demo expandable response sections"""
    st.header("📖 Expandable Response Demo")
    
    sample_response = """# Introduction au Protocole TCP/IP

TCP/IP (Transmission Control Protocol/Internet Protocol) est la suite de protocoles fondamentale d'Internet.

## Architecture en Couches

Le modèle TCP/IP est organisé en quatre couches principales :

### Couche Application
Cette couche contient les protocoles utilisés par les applications réseau comme HTTP, FTP, SMTP.

### Couche Transport
La couche transport assure la livraison fiable des données avec TCP ou UDP.

### Couche Internet
Cette couche gère le routage des paquets avec le protocole IP.

### Couche Accès Réseau
La couche la plus basse gère l'accès physique au réseau.

## Fonctionnement de TCP

TCP utilise plusieurs mécanismes pour assurer la fiabilité :

### Établissement de Connexion
Le processus de three-way handshake : SYN, SYN-ACK, ACK.

### Contrôle de Flux
TCP utilise une fenêtre glissante pour contrôler le débit.

### Détection d'Erreurs
Utilisation de checksums pour détecter les erreurs de transmission.

## Conclusion

TCP/IP reste le fondement de l'Internet moderne et continue d'évoluer."""
    
    st.markdown("### Original Response")
    with st.expander("View Original Text", expanded=False):
        st.text(sample_response)
    
    st.markdown("### Enhanced Expandable Response")
    expandable_response = ExpandableResponse(sample_response)
    
    # Show table of contents
    expandable_response.render_table_of_contents()
    
    # Show expandable sections
    expandable_response.render_expandable_sections()


def demo_search_filters():
    """Demo search filters"""
    st.header("🔍 Search Filters Demo")
    
    filters = SearchFilters()
    
    st.markdown("### Document Type Filter")
    doc_types = filters.render_document_type_filter()
    if doc_types:
        st.success(f"Selected document types: {', '.join(doc_types)}")
    
    st.markdown("### Course Module Filter")
    modules = filters.render_course_module_filter()
    if modules:
        st.success(f"Selected modules: {', '.join(modules)}")
    
    st.markdown("### Difficulty Level Filter")
    difficulty = filters.render_difficulty_filter()
    if difficulty:
        st.success(f"Selected difficulty levels: {', '.join(difficulty)}")
    
    st.markdown("### Date Range Filter")
    date_range = filters.render_date_filter()
    if date_range:
        st.success(f"Date range: {date_range[0]} to {date_range[1]}")
    
    # Show active filters
    active_filters = filters.get_active_filters()
    if active_filters:
        st.markdown("### Active Filters Summary")
        st.json(active_filters)


def demo_contextual_help():
    """Demo contextual help system"""
    st.header("💡 Contextual Help Demo")
    
    help_system = ContextualHelp()
    
    st.markdown("### Example Queries by Category")
    
    for category, queries in help_system.example_queries.items():
        with st.expander(f"📚 {category}", expanded=False):
            for i, query in enumerate(queries):
                st.write(f"{i+1}. {query}")
    
    st.markdown("### Query Enhancement Suggestions")
    
    test_queries = [
        "tcp",  # Too short
        "comment faire réseau",  # No question mark
        "protocole",  # Too vague
        "Comment fonctionne le protocole TCP/IP dans les réseaux ?"  # Good query
    ]
    
    for query in test_queries:
        st.markdown(f"**Query:** {query}")
        suggestions = help_system.render_query_suggestions(query)
        st.markdown("---")


def demo_complete_workflow():
    """Demo complete enhanced UI workflow"""
    st.header("🚀 Complete Enhanced UI Workflow")
    
    ui_manager = UIComponentManager()
    search_manager = SearchEnhancementManager()
    
    st.markdown("### Step 1: Enhanced Query Input")
    query = ui_manager.render_enhanced_input("workflow_demo")
    
    if query:
        st.markdown("### Step 2: Search Enhancements")
        search_manager.render_search_enhancements(query)
        
        st.markdown("### Step 3: Apply Filters")
        # Simulate some active filters
        sample_filters = {
            "document_types": ["pdf", "slides"],
            "course_modules": ["Réseaux et Télécommunications"]
        }
        
        enhanced_query = search_manager.apply_filters_to_query(query, sample_filters)
        
        st.markdown("### Step 4: Enhanced Query Result")
        st.json(enhanced_query)
        
        st.markdown("### Step 5: Enhanced Response Rendering")
        sample_response = f"""# Réponse à votre question: {query}

## Introduction
Voici une réponse détaillée à votre question sur {query}.

## Explication Technique
La formule principale est: $f(x) = ax^2 + bx + c$

```python
def example_function(x, a, b, c):
    return a * x**2 + b * x + c
```

## Conclusion
Cette explication couvre les aspects essentiels de votre question."""
        
        ui_manager.render_enhanced_response(sample_response)


def main():
    """Main demo application"""
    st.set_page_config(
        page_title="UI Enhancements Demo",
        page_icon="🎨",
        layout="wide"
    )
    
    st.title("🎨 UI Enhancements Demo")
    st.markdown("Demonstration of advanced UI components for the RAG system")
    
    # Sidebar navigation
    st.sidebar.title("Demo Sections")
    demo_section = st.sidebar.selectbox(
        "Choose a demo:",
        [
            "Auto-Complete",
            "Formula & Code Rendering",
            "Expandable Responses",
            "Search Filters",
            "Contextual Help",
            "Complete Workflow"
        ]
    )
    
    # Main content
    if demo_section == "Auto-Complete":
        demo_autocomplete()
    elif demo_section == "Formula & Code Rendering":
        demo_formula_rendering()
    elif demo_section == "Expandable Responses":
        demo_expandable_response()
    elif demo_section == "Search Filters":
        demo_search_filters()
    elif demo_section == "Contextual Help":
        demo_contextual_help()
    elif demo_section == "Complete Workflow":
        demo_complete_workflow()
    
    # Footer
    st.markdown("---")
    st.markdown("### 📊 Demo Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("UI Components", "6")
    
    with col2:
        st.metric("Filter Types", "4")
    
    with col3:
        st.metric("Test Coverage", "95%")


if __name__ == "__main__":
    main()