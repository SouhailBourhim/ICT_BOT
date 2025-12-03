#!/usr/bin/env python3
"""
Simple version of the RAG app for testing
"""

import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    import streamlit as st
    print("Streamlit is available")
    
    # Simple Streamlit app
    st.title("🎓 Assistant Virtuel - Smart ICT")
    st.write("This is a simple test version of the app.")
    
    # Test input
    user_input = st.text_input("Enter your question:")
    
    if user_input:
        st.write(f"You asked: {user_input}")
        st.write("This is a test response. The full RAG system requires additional setup.")
        
except ImportError as e:
    print(f"Streamlit not available: {e}")
    print("Please install streamlit first:")
    print("pip install streamlit")
    
except Exception as e:
    print(f"Error running app: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    print("Starting simple app...")