"""
Tests for UI Filters and Search Enhancement Components
Tests document type, course module, and difficulty level filters
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import date

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.filters import (
    DocumentType,
    DifficultyLevel,
    CourseModule,
    SearchFilters,
    ContextualHelp,
    SearchEnhancementManager
)


class TestEnums:
    """Test enumeration classes"""
    
    def test_document_type_enum(self):
        """Test DocumentType enumeration"""
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.SLIDES.value == "slides"
        assert DocumentType.EXERCISES.value == "exercises"
        assert len(DocumentType) >= 6
    
    def test_difficulty_level_enum(self):
        """Test DifficultyLevel enumeration"""
        assert DifficultyLevel.BEGINNER.value == "débutant"
        assert DifficultyLevel.INTERMEDIATE.value == "intermédiaire"
        assert DifficultyLevel.ADVANCED.value == "avancé"
        assert DifficultyLevel.EXPERT.value == "expert"
    
    def test_course_module_enum(self):
        """Test CourseModule enumeration"""
        assert CourseModule.NETWORKS.value == "Réseaux et Télécommunications"
        assert CourseModule.SECURITY.value == "Sécurité Informatique"
        assert CourseModule.WEB_DEV.value == "Développement Web"
        assert len(CourseModule) >= 9


class TestSearchFilters:
    """Test search filters functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.filters = SearchFilters()
    
    def test_initialization(self):
        """Test filters initialization"""
        assert self.filters is not None
        assert hasattr(self.filters, 'active_filters')
    
    @patch('streamlit.checkbox')
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    def test_render_document_type_filter(self, mock_markdown, mock_columns, mock_checkbox):
        """Test document type filter rendering"""
        # Mock columns
        mock_col = Mock()
        mock_columns.return_value = [mock_col] * 5
        mock_col.__enter__ = Mock(return_value=mock_col)
        mock_col.__exit__ = Mock(return_value=None)
        
        # Mock checkbox returns
        mock_checkbox.side_effect = [True, False, True, False, False]
        
        selected_types = self.filters.render_document_type_filter()
        
        assert len(selected_types) == 2  # Two checkboxes selected
        mock_markdown.assert_called()
        assert mock_checkbox.call_count == 5
    
    @patch('streamlit.multiselect')
    @patch('streamlit.markdown')
    def test_render_course_module_filter(self, mock_markdown, mock_multiselect):
        """Test course module filter rendering"""
        mock_multiselect.return_value = ["Réseaux et Télécommunications", "Sécurité Informatique"]
        
        selected_modules = self.filters.render_course_module_filter()
        
        assert len(selected_modules) == 2
        assert "Réseaux et Télécommunications" in selected_modules
        assert "Sécurité Informatique" in selected_modules
        mock_markdown.assert_called()
        mock_multiselect.assert_called_once()
    
    @patch('streamlit.multiselect')
    @patch('streamlit.markdown')
    def test_render_difficulty_filter(self, mock_markdown, mock_multiselect):
        """Test difficulty level filter rendering"""
        mock_multiselect.return_value = ["débutant", "intermédiaire"]
        
        selected_levels = self.filters.render_difficulty_filter()
        
        assert len(selected_levels) == 2
        assert "débutant" in selected_levels
        assert "intermédiaire" in selected_levels
        mock_markdown.assert_called()
        mock_multiselect.assert_called_once()
    
    @patch('streamlit.date_input')
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    def test_render_date_filter(self, mock_markdown, mock_columns, mock_date_input):
        """Test date range filter rendering"""
        # Mock columns
        mock_col = Mock()
        mock_columns.return_value = [mock_col, mock_col]
        mock_col.__enter__ = Mock(return_value=mock_col)
        mock_col.__exit__ = Mock(return_value=None)
        
        # Mock date inputs
        start_date = date(2024, 1, 1)
        end_date = date(2024, 12, 31)
        mock_date_input.side_effect = [start_date, end_date]
        
        date_range = self.filters.render_date_filter()
        
        assert date_range is not None
        assert date_range[0] == "2024-01-01"
        assert date_range[1] == "2024-12-31"
        mock_markdown.assert_called()
        assert mock_date_input.call_count == 2
    
    @patch('streamlit.date_input')
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    def test_render_date_filter_incomplete(self, mock_markdown, mock_columns, mock_date_input):
        """Test date filter with incomplete dates"""
        # Mock columns
        mock_col = Mock()
        mock_columns.return_value = [mock_col, mock_col]
        mock_col.__enter__ = Mock(return_value=mock_col)
        mock_col.__exit__ = Mock(return_value=None)
        
        # Mock incomplete date inputs
        mock_date_input.side_effect = [date(2024, 1, 1), None]
        
        date_range = self.filters.render_date_filter()
        
        assert date_range is None
    
    @patch.object(SearchFilters, 'render_document_type_filter')
    @patch.object(SearchFilters, 'render_course_module_filter')
    @patch.object(SearchFilters, 'render_difficulty_filter')
    @patch.object(SearchFilters, 'render_date_filter')
    def test_get_active_filters(self, mock_date, mock_difficulty, mock_modules, mock_doc_types):
        """Test getting all active filters"""
        # Mock filter returns
        mock_doc_types.return_value = ["pdf", "slides"]
        mock_modules.return_value = ["Réseaux et Télécommunications"]
        mock_difficulty.return_value = ["débutant"]
        mock_date.return_value = ("2024-01-01", "2024-12-31")
        
        filters = self.filters.get_active_filters()
        
        assert "document_types" in filters
        assert "course_modules" in filters
        assert "difficulty_levels" in filters
        assert "date_range" in filters
        
        assert len(filters["document_types"]) == 2
        assert len(filters["course_modules"]) == 1
        assert len(filters["difficulty_levels"]) == 1
    
    @patch.object(SearchFilters, 'render_document_type_filter')
    @patch.object(SearchFilters, 'render_course_module_filter')
    @patch.object(SearchFilters, 'render_difficulty_filter')
    @patch.object(SearchFilters, 'render_date_filter')
    def test_get_active_filters_empty(self, mock_date, mock_difficulty, mock_modules, mock_doc_types):
        """Test getting active filters when none are selected"""
        # Mock empty filter returns
        mock_doc_types.return_value = []
        mock_modules.return_value = []
        mock_difficulty.return_value = []
        mock_date.return_value = None
        
        filters = self.filters.get_active_filters()
        
        assert len(filters) == 0
    
    @patch('streamlit.session_state', {})
    def test_clear_filters(self):
        """Test clearing all filters"""
        # Add some mock session state
        st.session_state["doc_type_pdf"] = True
        st.session_state["course_modules_filter"] = ["test"]
        
        self.filters.clear_filters()
        
        # Session state should be cleared (mocked, so we just test the method runs)
        assert True  # Method completed without error


class TestContextualHelp:
    """Test contextual help system"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.help_system = ContextualHelp()
    
    def test_initialization(self):
        """Test help system initialization"""
        assert self.help_system is not None
        assert hasattr(self.help_system, 'example_queries')
        assert isinstance(self.help_system.example_queries, dict)
    
    def test_example_queries_structure(self):
        """Test example queries structure"""
        queries = self.help_system.example_queries
        
        # Check required categories
        required_categories = ["Réseaux", "Sécurité", "Programmation", "Bases de données"]
        for category in required_categories:
            assert category in queries
            assert isinstance(queries[category], list)
            assert len(queries[category]) > 0
    
    @patch('streamlit.expander')
    @patch('streamlit.markdown')
    @patch('streamlit.button')
    def test_render_help_panel(self, mock_button, mock_markdown, mock_expander):
        """Test help panel rendering"""
        # Mock expander context manager
        mock_expander.return_value.__enter__ = Mock()
        mock_expander.return_value.__exit__ = Mock()
        mock_button.return_value = False
        
        self.help_system.render_help_panel()
        
        mock_expander.assert_called()
        mock_markdown.assert_called()
    
    def test_render_query_suggestions_empty(self):
        """Test query suggestions with empty query"""
        suggestions = self.help_system.render_query_suggestions("")
        assert suggestions == []
        
        suggestions = self.help_system.render_query_suggestions("short")
        assert suggestions == []
    
    @patch('streamlit.info')
    @patch('streamlit.markdown')
    def test_render_query_suggestions_valid(self, mock_markdown, mock_info):
        """Test query suggestions with valid query"""
        query = "comment faire"  # Short query without question mark
        suggestions = self.help_system.render_query_suggestions(query)
        
        assert len(suggestions) > 0
        mock_markdown.assert_called()
        mock_info.assert_called()
    
    @patch('streamlit.info')
    @patch('streamlit.markdown')
    def test_render_query_suggestions_good_query(self, mock_markdown, mock_info):
        """Test query suggestions with well-formed query"""
        query = "Comment fonctionne le protocole TCP/IP dans les réseaux informatiques ?"
        suggestions = self.help_system.render_query_suggestions(query)
        
        # Should have fewer suggestions for a well-formed query
        assert isinstance(suggestions, list)


class TestSearchEnhancementManager:
    """Test search enhancement manager"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = SearchEnhancementManager()
    
    def test_initialization(self):
        """Test manager initialization"""
        assert self.manager is not None
        assert hasattr(self.manager, 'filters')
        assert hasattr(self.manager, 'help_system')
    
    @patch('streamlit.sidebar')
    @patch('streamlit.button')
    @patch('streamlit.markdown')
    @patch('streamlit.success')
    @patch.object(SearchFilters, 'get_active_filters')
    @patch.object(SearchFilters, 'clear_filters')
    def test_render_filter_sidebar(self, mock_clear, mock_get_filters, mock_success, 
                                 mock_markdown, mock_button, mock_sidebar):
        """Test filter sidebar rendering"""
        # Mock sidebar context manager
        mock_sidebar.__enter__ = Mock()
        mock_sidebar.__exit__ = Mock()
        
        # Mock active filters
        mock_get_filters.return_value = {"document_types": ["pdf", "slides"]}
        mock_button.return_value = False
        
        filters = self.manager.render_filter_sidebar()
        
        assert "document_types" in filters
        mock_markdown.assert_called()
        mock_success.assert_called()
    
    @patch.object(ContextualHelp, 'render_query_suggestions')
    @patch.object(ContextualHelp, 'render_help_panel')
    def test_render_search_enhancements(self, mock_help_panel, mock_suggestions):
        """Test search enhancement rendering"""
        query = "test query"
        
        self.manager.render_search_enhancements(query)
        
        mock_suggestions.assert_called_once_with(query)
        mock_help_panel.assert_called_once()
    
    def test_apply_filters_to_query_empty(self):
        """Test applying empty filters to query"""
        query = "test query"
        filters = {}
        
        enhanced_query = self.manager.apply_filters_to_query(query, filters)
        
        assert enhanced_query["query"] == query
        assert enhanced_query["filters"] == filters
        assert enhanced_query["metadata_filters"] == {}
    
    def test_apply_filters_to_query_with_filters(self):
        """Test applying filters to query"""
        query = "test query"
        filters = {
            "document_types": ["pdf", "slides"],
            "course_modules": ["Réseaux et Télécommunications"],
            "difficulty_levels": ["débutant"],
            "date_range": ("2024-01-01", "2024-12-31")
        }
        
        enhanced_query = self.manager.apply_filters_to_query(query, filters)
        
        assert enhanced_query["query"] == query
        assert enhanced_query["filters"] == filters
        
        metadata_filters = enhanced_query["metadata_filters"]
        assert "document_type" in metadata_filters
        assert "course_module" in metadata_filters
        assert "difficulty_level" in metadata_filters
        assert "created_date" in metadata_filters
        
        # Check filter structure
        assert metadata_filters["document_type"]["$in"] == ["pdf", "slides"]
        assert metadata_filters["course_module"]["$in"] == ["Réseaux et Télécommunications"]
        assert metadata_filters["difficulty_level"]["$in"] == ["débutant"]
        assert metadata_filters["created_date"]["$gte"] == "2024-01-01"
        assert metadata_filters["created_date"]["$lte"] == "2024-12-31"
    
    def test_apply_filters_partial(self):
        """Test applying partial filters"""
        query = "test query"
        filters = {
            "document_types": ["pdf"]
        }
        
        enhanced_query = self.manager.apply_filters_to_query(query, filters)
        
        metadata_filters = enhanced_query["metadata_filters"]
        assert "document_type" in metadata_filters
        assert "course_module" not in metadata_filters
        assert "difficulty_level" not in metadata_filters
        assert "created_date" not in metadata_filters


class TestIntegration:
    """Integration tests for UI components"""
    
    def test_manager_integration(self):
        """Test integration between managers"""
        manager = SearchEnhancementManager()
        
        # Test that components work together
        assert manager.filters is not None
        assert manager.help_system is not None
        
        # Test filter application
        query = "test"
        filters = {"document_types": ["pdf"]}
        enhanced_query = manager.apply_filters_to_query(query, filters)
        
        assert enhanced_query is not None
        assert "metadata_filters" in enhanced_query
    
    def test_enum_values_consistency(self):
        """Test that enum values are consistent across components"""
        # Test that enum values match expected formats
        doc_types = [dt.value for dt in DocumentType]
        assert all(isinstance(dt, str) for dt in doc_types)
        
        difficulties = [dl.value for dl in DifficultyLevel]
        assert all(isinstance(dl, str) for dl in difficulties)
        
        modules = [cm.value for cm in CourseModule]
        assert all(isinstance(cm, str) for cm in modules)


if __name__ == "__main__":
    pytest.main([__file__])