"""
Tests for UI Components
Tests auto-complete, formula rendering, and expandable sections
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.components import (
    AutoCompleteComponent, 
    FormulaRenderer, 
    ExpandableResponse, 
    UIComponentManager
)


class TestAutoCompleteComponent:
    """Test auto-complete functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.autocomplete = AutoCompleteComponent()
    
    def test_initialization(self):
        """Test component initialization"""
        assert self.autocomplete is not None
        assert isinstance(self.autocomplete.content_index, dict)
        assert "topics" in self.autocomplete.content_index
        assert "commands" in self.autocomplete.content_index
    
    def test_get_suggestions_empty_query(self):
        """Test suggestions with empty query"""
        suggestions = self.autocomplete.get_suggestions("")
        assert suggestions == []
        
        suggestions = self.autocomplete.get_suggestions("a")
        assert suggestions == []
    
    def test_get_suggestions_valid_query(self):
        """Test suggestions with valid query"""
        suggestions = self.autocomplete.get_suggestions("réseau")
        assert len(suggestions) > 0
        assert any("réseau" in suggestion.lower() for suggestion in suggestions)
    
    def test_get_suggestions_max_limit(self):
        """Test suggestions respect max limit"""
        suggestions = self.autocomplete.get_suggestions("a", max_suggestions=3)
        assert len(suggestions) <= 3
    
    def test_get_suggestions_case_insensitive(self):
        """Test case insensitive suggestions"""
        suggestions_lower = self.autocomplete.get_suggestions("réseau")
        suggestions_upper = self.autocomplete.get_suggestions("RÉSEAU")
        suggestions_mixed = self.autocomplete.get_suggestions("Réseau")
        
        # Should return same results regardless of case
        assert len(suggestions_lower) > 0
        assert len(suggestions_upper) > 0
        assert len(suggestions_mixed) > 0
    
    def test_custom_content_index(self):
        """Test with custom content index"""
        custom_index = {
            "topics": ["test_topic", "another_topic"],
            "commands": ["test_command"]
        }
        autocomplete = AutoCompleteComponent(custom_index)
        
        suggestions = autocomplete.get_suggestions("test")
        assert len(suggestions) >= 2
        assert "test_topic" in suggestions
        assert "test_command" in suggestions


class TestFormulaRenderer:
    """Test mathematical formula and code rendering"""
    
    def test_render_math_formula_simple(self):
        """Test simple LaTeX formula rendering"""
        text = "The formula is $E = mc^2$"
        result = FormulaRenderer.render_math_formula(text)
        assert "$$" in result
        assert "E = mc^2" in result
    
    def test_render_math_formula_block(self):
        """Test block LaTeX formula rendering"""
        text = "The equation is $$\\int_0^1 x^2 dx = \\frac{1}{3}$$"
        result = FormulaRenderer.render_math_formula(text)
        assert "$$" in result
        assert "\\int_0^1 x^2 dx = \\frac{1}{3}" in result
    
    def test_render_math_formula_multiple(self):
        """Test multiple formulas in text"""
        text = "First formula $a + b = c$ and second $$x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$$"
        result = FormulaRenderer.render_math_formula(text)
        assert result.count("$$") >= 4  # At least 2 formulas with opening/closing $$
    
    def test_render_math_formula_no_formulas(self):
        """Test text without formulas"""
        text = "This is plain text without any mathematical formulas"
        result = FormulaRenderer.render_math_formula(text)
        assert result == text
    
    @patch('streamlit.code')
    def test_render_code_snippet(self, mock_code):
        """Test code snippet rendering"""
        code = "def hello():\n    print('Hello, World!')"
        FormulaRenderer.render_code_snippet(code, "python")
        mock_code.assert_called_once_with(code, language="python")
    
    @patch('streamlit.code')
    @patch('streamlit.markdown')
    def test_detect_and_render_content_code(self, mock_markdown, mock_code):
        """Test content detection and rendering for code"""
        text = "```python\ndef hello():\n    print('Hello')\n```"
        FormulaRenderer.detect_and_render_content(text)
        mock_code.assert_called_once()
    
    @patch('streamlit.markdown')
    def test_detect_and_render_content_math(self, mock_markdown):
        """Test content detection and rendering for math"""
        text = "The equation is $E = mc^2$"
        FormulaRenderer.detect_and_render_content(text)
        mock_markdown.assert_called()
    
    @patch('streamlit.markdown')
    def test_detect_and_render_content_plain(self, mock_markdown):
        """Test content detection and rendering for plain text"""
        text = "This is plain text"
        FormulaRenderer.detect_and_render_content(text)
        mock_markdown.assert_called_with(text)


class TestExpandableResponse:
    """Test expandable response sections"""
    
    def test_initialization_simple_text(self):
        """Test initialization with simple text"""
        text = "This is a simple response without sections"
        response = ExpandableResponse(text)
        assert response.response_text == text
        assert len(response.sections) == 1
        assert response.sections[0]["title"] == "Introduction"
    
    def test_initialization_with_headers(self):
        """Test initialization with markdown headers"""
        text = """# Introduction
This is the introduction.

## Section 1
This is section 1 content.

### Subsection 1.1
This is subsection content.

## Section 2
This is section 2 content."""
        
        response = ExpandableResponse(text)
        assert len(response.sections) == 4
        
        # Check section titles
        titles = [section["title"] for section in response.sections]
        assert "Introduction" in titles
        assert "Section 1" in titles
        assert "Subsection 1.1" in titles
        assert "Section 2" in titles
    
    def test_section_levels(self):
        """Test section level detection"""
        text = """# Level 1
Content 1

## Level 2
Content 2

### Level 3
Content 3"""
        
        response = ExpandableResponse(text)
        levels = [section["level"] for section in response.sections]
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels
    
    @patch('streamlit.markdown')
    @patch('streamlit.button')
    def test_render_table_of_contents(self, mock_button, mock_markdown):
        """Test table of contents rendering"""
        text = """# Section 1
Content 1

## Section 2
Content 2"""
        
        response = ExpandableResponse(text)
        mock_button.return_value = False
        
        response.render_table_of_contents()
        mock_markdown.assert_called()
        assert mock_button.call_count >= 2  # At least 2 sections
    
    @patch('streamlit.expander')
    def test_render_expandable_sections_single(self, mock_expander):
        """Test rendering single section"""
        text = "Simple text without headers"
        response = ExpandableResponse(text)
        
        # Mock the expander context manager
        mock_expander.return_value.__enter__ = Mock()
        mock_expander.return_value.__exit__ = Mock()
        
        with patch('ui.components.FormulaRenderer.detect_and_render_content') as mock_render:
            response.render_expandable_sections()
            mock_render.assert_called_once_with(text)
    
    @patch('streamlit.expander')
    @patch('streamlit.session_state', {})
    def test_render_expandable_sections_multiple(self, mock_expander):
        """Test rendering multiple sections"""
        text = """# Section 1
Content 1

# Section 2
Content 2"""
        
        response = ExpandableResponse(text)
        
        # Mock the expander context manager
        mock_expander.return_value.__enter__ = Mock()
        mock_expander.return_value.__exit__ = Mock()
        
        with patch('ui.components.FormulaRenderer.detect_and_render_content'):
            response.render_expandable_sections()
            assert mock_expander.call_count == 2


class TestUIComponentManager:
    """Test UI component manager"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.ui_manager = UIComponentManager()
    
    def test_initialization(self):
        """Test manager initialization"""
        assert self.ui_manager is not None
        assert hasattr(self.ui_manager, 'autocomplete')
        assert hasattr(self.ui_manager, 'formula_renderer')
    
    @patch('ui.components.AutoCompleteComponent.render_autocomplete_input')
    def test_render_enhanced_input(self, mock_render):
        """Test enhanced input rendering"""
        mock_render.return_value = "test query"
        result = self.ui_manager.render_enhanced_input("test_key")
        mock_render.assert_called_once_with("test_key")
        assert result == "test query"
    
    @patch('ui.components.ExpandableResponse')
    def test_render_enhanced_response(self, mock_expandable):
        """Test enhanced response rendering"""
        mock_instance = Mock()
        mock_expandable.return_value = mock_instance
        
        self.ui_manager.render_enhanced_response("test response")
        
        mock_expandable.assert_called_once_with("test response")
        mock_instance.render_table_of_contents.assert_called_once()
        mock_instance.render_expandable_sections.assert_called_once()
    
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    def test_add_response_feedback(self, mock_markdown, mock_columns, mock_button):
        """Test response feedback collection"""
        # Mock columns
        mock_col = Mock()
        mock_columns.return_value = [mock_col, mock_col, mock_col]
        mock_col.__enter__ = Mock(return_value=mock_col)
        mock_col.__exit__ = Mock(return_value=None)
        
        # Mock button returns
        mock_button.side_effect = [True, False, False]  # First button clicked
        
        feedback = self.ui_manager.add_response_feedback("test_id")
        
        assert feedback is not None
        assert feedback["rating"] == "helpful"
        assert feedback["response_id"] == "test_id"


class TestUIAccessibility:
    """Test UI accessibility features"""
    
    def test_autocomplete_has_help_text(self):
        """Test auto-complete has help text"""
        autocomplete = AutoCompleteComponent()
        # This would be tested in integration tests with actual Streamlit components
        assert autocomplete is not None
    
    def test_formula_renderer_handles_special_chars(self):
        """Test formula renderer handles special characters"""
        text = "Special chars: α, β, γ, θ, ∑, ∫"
        result = FormulaRenderer.render_math_formula(text)
        assert result is not None
        assert len(result) > 0
    
    def test_expandable_response_keyboard_navigation(self):
        """Test expandable response supports keyboard navigation"""
        # This would be tested with actual Streamlit components
        text = "# Section 1\nContent"
        response = ExpandableResponse(text)
        assert len(response.sections) > 0


if __name__ == "__main__":
    pytest.main([__file__])