"""
Streamlit compatibility utilities for different versions.
"""
import streamlit as st


def safe_rerun():
    """
    Safely trigger a Streamlit rerun with fallback for older versions.
    """
    try:
        # Try new method (Streamlit >= 1.27.0)
        st.rerun()
    except AttributeError:
        try:
            # Try experimental method (older versions)
            st.experimental_rerun()
        except AttributeError:
            # No rerun available, continue without it
            pass


def safe_toggle(label: str, value: bool = False, key: str = None, help: str = None):
    """
    Safely create a toggle widget with fallback to checkbox for older versions.
    """
    try:
        # Try new toggle widget (Streamlit >= 1.28.0)
        return st.toggle(label, value=value, key=key, help=help)
    except AttributeError:
        # Fallback to checkbox for older versions
        return st.checkbox(label, value=value, key=key, help=help)


def get_streamlit_version():
    """
    Get the current Streamlit version.
    """
    try:
        return st.__version__
    except AttributeError:
        return "unknown"


def check_streamlit_features():
    """
    Check which Streamlit features are available.
    """
    features = {
        "rerun": hasattr(st, 'rerun'),
        "experimental_rerun": hasattr(st, 'experimental_rerun'),
        "toggle": hasattr(st, 'toggle'),
        "tabs": hasattr(st, 'tabs'),
        "columns": hasattr(st, 'columns'),
        "expander": hasattr(st, 'expander'),
        "container": hasattr(st, 'container'),
        "empty": hasattr(st, 'empty'),
        "form": hasattr(st, 'form'),
        "cache_data": hasattr(st, 'cache_data'),
        "cache_resource": hasattr(st, 'cache_resource'),
    }
    
    return {
        "version": get_streamlit_version(),
        "features": features
    }


# Convenience aliases
rerun = safe_rerun
toggle = safe_toggle