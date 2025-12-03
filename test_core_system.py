#!/usr/bin/env python3
"""
Test script for the core RAG system without Streamlit dependencies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_basic_imports():
    """Test basic imports without Streamlit."""
    print("Testing basic imports...")
    
    try:
        # Test core imports
        from langchain_ollama import OllamaEmbeddings, ChatOllama
        print("✅ LangChain Ollama imports successful")
        
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_classic.chains import create_retrieval_chain
        from langchain_classic.chains.combine_documents import create_stuff_documents_chain
        print("✅ LangChain core imports successful")
        
        import pypdf
        print("✅ PyPDF import successful")
        
        from rank_bm25 import BM25Okapi
        print("✅ BM25 import successful")
        
        import psutil
        print("✅ psutil import successful")
        
        from dotenv import load_dotenv
        print("✅ python-dotenv import successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from config.settings import get_settings
        config = get_settings()
        print(f"✅ Configuration loaded successfully")
        print(f"   - Model: {config.model.ollama_model}")
        print(f"   - Database path: {config.database.chroma_path}")
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_core_system():
    """Test core system initialization."""
    print("\nTesting core system...")
    
    try:
        from src.core.system import RAGSystem
        
        # Initialize system
        rag_system = RAGSystem()
        print("✅ RAG System created")
        
        # Try to initialize (this might fail if Ollama isn't running)
        try:
            rag_system.initialize()
            print("✅ RAG System initialized successfully")
            return True
        except Exception as e:
            print(f"⚠️  RAG System initialization failed (Ollama may not be running): {e}")
            return False
            
    except Exception as e:
        print(f"❌ Core system error: {e}")
        return False

def test_managers():
    """Test manager classes."""
    print("\nTesting managers...")
    
    try:
        from src.managers.conversation_manager import ConversationManager
        from src.managers.response_manager import ResponseManager
        from src.managers.query_enhancer import QueryEnhancer
        from src.managers.analytics_manager import AnalyticsManager
        
        # Create managers
        conversation_manager = ConversationManager()
        response_manager = ResponseManager()
        query_enhancer = QueryEnhancer()
        analytics_manager = AnalyticsManager()
        
        print("✅ All managers created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Manager error: {e}")
        return False

def test_simple_query():
    """Test a simple query without full system."""
    print("\nTesting simple query...")
    
    try:
        from config.settings import get_settings
        config = get_settings()
        
        # Test basic LLM connection
        from langchain_ollama import ChatOllama
        
        llm = ChatOllama(model=config.model.ollama_model)
        print("✅ LLM connection created")
        
        # Test simple prompt
        from langchain_core.prompts import ChatPromptTemplate
        
        prompt_template = ChatPromptTemplate.from_template(
            "You are a helpful assistant. Answer this question: {question}"
        )
        
        chain = prompt_template | llm
        
        # Try a simple query
        try:
            response = chain.invoke({"question": "What is 2+2?"})
            print(f"✅ Simple query successful: {response.content[:100]}...")
            return True
        except Exception as e:
            print(f"⚠️  Query failed (Ollama may not be running): {e}")
            return False
            
    except Exception as e:
        print(f"❌ Query test error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing ICT Bot Core System")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_config,
        test_managers,
        test_core_system,
        test_simple_query
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Core system is working.")
    elif passed >= total - 1:
        print("✅ Core system is mostly working. Check Ollama connection.")
    else:
        print("❌ Core system has issues. Check dependencies.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)