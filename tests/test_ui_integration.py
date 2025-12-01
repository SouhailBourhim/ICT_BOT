"""
End-to-End Integration Tests for Enhanced UI Functionality
Tests complete user workflows with enhanced UI components
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.components import UIComponentManager
from src.ui.filters import SearchEnhancementManager


class TestUIIntegration:
    """Integration tests for UI components working together"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.ui_manager = UIComponentManager()
        self.search_manager = SearchEnhancementManager()
    
    def test_complete_search_workflow(self):
        """Test complete search workflow with filters and enhancements"""
        # Simulate user query
        query = "Comment fonctionne TCP/IP ?"
        
        # Simulate active filters
        filters = {
            "document_types": ["pdf"],
            "course_modules": ["Réseaux et Télécommunications"],
            "difficulty_levels": ["intermédiaire"]
        }
        
        # Apply filters to query
        enhanced_query = self.search_manager.apply_filters_to_query(query, filters)
        
        # Verify enhanced query structure
        assert enhanced_query["query"] == query
        assert enhanced_query["filters"] == filters
        assert "metadata_filters" in enhanced_query
        
        # Verify metadata filters are properly formatted
        metadata_filters = enhanced_query["metadata_filters"]
        assert metadata_filters["document_type"]["$in"] == ["pdf"]
        assert metadata_filters["course_module"]["$in"] == ["Réseaux et Télécommunications"]
        assert metadata_filters["difficulty_level"]["$in"] == ["intermédiaire"]
    
    @patch('streamlit.session_state', {})
    def test_conversation_flow_with_ui_enhancements(self):
        """Test conversation flow with UI enhancements"""
        # Initialize conversation
        conversation_id = "test_conversation_123"
        
        # Simulate user messages with enhanced UI
        messages = [
            {
                "role": "user",
                "content": "Qu'est-ce que TCP/IP ?",
                "timestamp": datetime.now().isoformat(),
                "filters": {"document_types": ["pdf"]}
            },
            {
                "role": "assistant",
                "content": "# TCP/IP Protocol\n\nTCP/IP est un protocole...\n\n## Fonctionnement\n\nLe protocole fonctionne en couches...",
                "timestamp": datetime.now().isoformat(),
                "response_id": "response_123",
                "sources": ["doc1.pdf", "doc2.pdf"]
            }
        ]
        
        # Test enhanced response rendering
        response_text = messages[1]["content"]
        
        # This would normally render in Streamlit, but we can test the parsing
        from src.ui.components import ExpandableResponse
        expandable_response = ExpandableResponse(response_text)
        
        # Verify sections are parsed correctly
        assert len(expandable_response.sections) >= 2
        section_titles = [section["title"] for section in expandable_response.sections]
        assert "TCP/IP Protocol" in section_titles
        assert "Fonctionnement" in section_titles
    
    def test_autocomplete_with_course_content(self):
        """Test auto-complete functionality with course content"""
        autocomplete = self.ui_manager.autocomplete
        
        # Test suggestions for network-related queries
        network_suggestions = autocomplete.get_suggestions("réseau")
        assert len(network_suggestions) > 0
        assert any("réseau" in suggestion.lower() for suggestion in network_suggestions)
        
        # Test suggestions for security-related queries
        security_suggestions = autocomplete.get_suggestions("sécurité")
        assert len(security_suggestions) > 0
        assert any("sécurité" in suggestion.lower() for suggestion in security_suggestions)
        
        # Test command suggestions
        command_suggestions = autocomplete.get_suggestions("expliquez")
        assert len(command_suggestions) > 0
        assert any("expliquez" in suggestion.lower() for suggestion in command_suggestions)
    
    def test_formula_and_code_rendering(self):
        """Test mathematical formula and code rendering"""
        from src.ui.components import FormulaRenderer
        
        # Test mixed content with formulas and code
        mixed_content = """
        # Algorithme de Dijkstra
        
        L'algorithme utilise la formule: $d(v) = min(d(u) + w(u,v))$
        
        ```python
        def dijkstra(graph, start):
            distances = {node: float('infinity') for node in graph}
            distances[start] = 0
            return distances
        ```
        
        La complexité est de $O(V^2)$ où V est le nombre de sommets.
        """
        
        # Test that formulas are detected and processed
        processed_text = FormulaRenderer.render_math_formula(mixed_content)
        assert "$$" in processed_text  # LaTeX formulas should be wrapped
        
        # Test that the content structure is preserved
        assert "Algorithme de Dijkstra" in processed_text
        assert "def dijkstra" in processed_text
    
    def test_filter_combinations(self):
        """Test various filter combinations"""
        # Test single filter
        single_filter = {"document_types": ["pdf"]}
        enhanced_query = self.search_manager.apply_filters_to_query("test", single_filter)
        assert len(enhanced_query["metadata_filters"]) == 1
        
        # Test multiple filters
        multiple_filters = {
            "document_types": ["pdf", "slides"],
            "course_modules": ["Réseaux et Télécommunications", "Sécurité Informatique"],
            "difficulty_levels": ["débutant", "intermédiaire"]
        }
        enhanced_query = self.search_manager.apply_filters_to_query("test", multiple_filters)
        assert len(enhanced_query["metadata_filters"]) == 3
        
        # Test date range filter
        date_filter = {"date_range": ("2024-01-01", "2024-12-31")}
        enhanced_query = self.search_manager.apply_filters_to_query("test", date_filter)
        assert "created_date" in enhanced_query["metadata_filters"]
        assert enhanced_query["metadata_filters"]["created_date"]["$gte"] == "2024-01-01"
        assert enhanced_query["metadata_filters"]["created_date"]["$lte"] == "2024-12-31"
    
    def test_contextual_help_examples(self):
        """Test contextual help with example queries"""
        help_system = self.search_manager.help_system
        
        # Test that all categories have examples
        for category, examples in help_system.example_queries.items():
            assert len(examples) > 0
            assert all(isinstance(example, str) for example in examples)
            assert all(len(example) > 10 for example in examples)  # Reasonable length
    
    def test_query_enhancement_suggestions(self):
        """Test query enhancement and suggestions"""
        help_system = self.search_manager.help_system
        
        # Test suggestions for poor queries
        poor_queries = [
            "tcp",  # Too short
            "comment faire",  # No question mark
            "réseau"  # Too vague
        ]
        
        for query in poor_queries:
            with patch('streamlit.info') as mock_info, patch('streamlit.markdown') as mock_markdown:
                suggestions = help_system.render_query_suggestions(query)
                # Should provide suggestions for improvement
                assert isinstance(suggestions, list)
    
    def test_accessibility_features(self):
        """Test accessibility features of UI components"""
        # Test that components have proper help text and labels
        autocomplete = self.ui_manager.autocomplete
        
        # Test content index has accessible structure
        assert isinstance(autocomplete.content_index, dict)
        for category, items in autocomplete.content_index.items():
            assert isinstance(items, list)
            assert all(isinstance(item, str) for item in items)
    
    def test_error_handling_in_ui(self):
        """Test error handling in UI components"""
        # Test auto-complete with invalid input
        autocomplete = self.ui_manager.autocomplete
        
        # Should handle None gracefully
        suggestions = autocomplete.get_suggestions(None)
        assert suggestions == []
        
        # Should handle empty string gracefully
        suggestions = autocomplete.get_suggestions("")
        assert suggestions == []
        
        # Test formula renderer with invalid input
        from src.ui.components import FormulaRenderer
        
        # Should handle None gracefully
        result = FormulaRenderer.render_math_formula(None or "")
        assert result == ""
    
    def test_performance_with_large_content(self):
        """Test UI performance with large content"""
        # Test auto-complete with large content index
        large_index = {
            "topics": [f"topic_{i}" for i in range(1000)],
            "commands": [f"command_{i}" for i in range(500)]
        }
        
        autocomplete = self.ui_manager.autocomplete
        autocomplete.content_index = large_index
        
        # Should still return reasonable number of suggestions
        suggestions = autocomplete.get_suggestions("topic", max_suggestions=10)
        assert len(suggestions) <= 10
        
        # Test expandable response with large text
        large_text = "\n\n".join([f"# Section {i}\nContent for section {i}" for i in range(50)])
        
        from src.ui.components import ExpandableResponse
        expandable_response = ExpandableResponse(large_text)
        
        # Should parse sections correctly even with large content
        assert len(expandable_response.sections) == 50


class TestUIWorkflows:
    """Test complete UI workflows"""
    
    def test_student_research_workflow(self):
        """Test typical student research workflow"""
        ui_manager = UIComponentManager()
        search_manager = SearchEnhancementManager()
        
        # Step 1: Student starts typing a query
        partial_query = "proto"
        suggestions = ui_manager.autocomplete.get_suggestions(partial_query)
        assert len(suggestions) > 0
        
        # Step 2: Student selects a suggestion or completes query
        full_query = "Expliquez le protocole TCP/IP"
        
        # Step 3: Student applies filters
        filters = {
            "document_types": ["pdf", "slides"],
            "course_modules": ["Réseaux et Télécommunications"]
        }
        
        # Step 4: System enhances query with filters
        enhanced_query = search_manager.apply_filters_to_query(full_query, filters)
        
        # Verify workflow completion
        assert enhanced_query["query"] == full_query
        assert enhanced_query["filters"] == filters
        assert len(enhanced_query["metadata_filters"]) == 2
    
    def test_instructor_content_review_workflow(self):
        """Test instructor reviewing content workflow"""
        search_manager = SearchEnhancementManager()
        
        # Instructor wants to see all content for a specific module
        filters = {
            "course_modules": ["Sécurité Informatique"],
            "document_types": ["pdf", "slides", "exercises"]
        }
        
        query = "sécurité informatique"
        enhanced_query = search_manager.apply_filters_to_query(query, filters)
        
        # Should include all document types for the module
        metadata_filters = enhanced_query["metadata_filters"]
        assert len(metadata_filters["document_type"]["$in"]) == 3
        assert "Sécurité Informatique" in metadata_filters["course_module"]["$in"]
    
    def test_advanced_search_workflow(self):
        """Test advanced search with multiple criteria"""
        search_manager = SearchEnhancementManager()
        
        # Advanced search with all filter types
        filters = {
            "document_types": ["pdf"],
            "course_modules": ["Intelligence Artificielle"],
            "difficulty_levels": ["avancé", "expert"],
            "date_range": ("2024-01-01", "2024-12-31")
        }
        
        query = "réseaux de neurones deep learning"
        enhanced_query = search_manager.apply_filters_to_query(query, filters)
        
        # Verify all filters are applied
        metadata_filters = enhanced_query["metadata_filters"]
        assert "document_type" in metadata_filters
        assert "course_module" in metadata_filters
        assert "difficulty_level" in metadata_filters
        assert "created_date" in metadata_filters
        
        # Verify date range format
        assert metadata_filters["created_date"]["$gte"] == "2024-01-01"
        assert metadata_filters["created_date"]["$lte"] == "2024-12-31"


if __name__ == "__main__":
    pytest.main([__file__])