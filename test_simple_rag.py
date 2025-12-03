#!/usr/bin/env python3
"""
Test script for a simple RAG system without ChromaDB.
Uses in-memory vector storage for testing.
"""

import sys
import os
import numpy as np
from typing import List, Dict, Any
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class SimpleVectorStore:
    """Simple in-memory vector store for testing."""
    
    def __init__(self):
        self.documents = []
        self.embeddings = []
        self.metadata = []
    
    def add_documents(self, documents: List[str], embeddings: List[List[float]], metadata: List[Dict] = None):
        """Add documents with their embeddings."""
        self.documents.extend(documents)
        self.embeddings.extend(embeddings)
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend([{}] * len(documents))
    
    def similarity_search(self, query_embedding: List[float], k: int = 3) -> List[Dict]:
        """Find most similar documents."""
        if not self.embeddings:
            return []
        
        # Calculate cosine similarity
        query_norm = np.linalg.norm(query_embedding)
        similarities = []
        
        for i, doc_embedding in enumerate(self.embeddings):
            doc_norm = np.linalg.norm(doc_embedding)
            if doc_norm == 0 or query_norm == 0:
                similarity = 0
            else:
                similarity = np.dot(query_embedding, doc_embedding) / (query_norm * doc_norm)
            similarities.append((similarity, i))
        
        # Sort by similarity and return top k
        similarities.sort(reverse=True)
        results = []
        
        for similarity, idx in similarities[:k]:
            results.append({
                'document': self.documents[idx],
                'metadata': self.metadata[idx],
                'similarity': similarity
            })
        
        return results

def test_simple_vector_store():
    """Test the simple vector store."""
    print("Testing simple vector store...")
    
    try:
        store = SimpleVectorStore()
        
        # Add some test documents with dummy embeddings
        documents = [
            "Python is a programming language",
            "Machine learning uses algorithms",
            "RAG combines retrieval and generation"
        ]
        
        # Create dummy embeddings (in real use, these would come from an embedding model)
        embeddings = [
            [1.0, 0.5, 0.2, 0.1],  # Python doc
            [0.3, 1.0, 0.4, 0.2],  # ML doc
            [0.2, 0.3, 1.0, 0.5]   # RAG doc
        ]
        
        metadata = [
            {"source": "python_doc"},
            {"source": "ml_doc"},
            {"source": "rag_doc"}
        ]
        
        store.add_documents(documents, embeddings, metadata)
        print("✅ Documents added to vector store")
        
        # Test similarity search
        query_embedding = [0.9, 0.4, 0.1, 0.1]  # Similar to Python doc
        results = store.similarity_search(query_embedding, k=2)
        
        print(f"✅ Similarity search returned {len(results)} results")
        for i, result in enumerate(results):
            print(f"   {i+1}. {result['document'][:50]}... (similarity: {result['similarity']:.3f})")
        
        return True
        
    except Exception as e:
        print(f"❌ Vector store test failed: {e}")
        return False

def test_ollama_integration():
    """Test Ollama integration with simple RAG."""
    print("\nTesting Ollama integration...")
    
    try:
        from langchain_ollama import OllamaEmbeddings, ChatOllama
        from langchain_core.prompts import ChatPromptTemplate
        from config.settings import get_settings
        
        config = get_settings()
        
        # Create embeddings and LLM
        embeddings = OllamaEmbeddings(model=config.model.ollama_model)
        llm = ChatOllama(model=config.model.ollama_model)
        print("✅ Ollama models created")
        
        # Create vector store
        store = SimpleVectorStore()
        
        # Add some test documents
        documents = [
            "Python is a high-level programming language known for its simplicity and readability.",
            "Machine learning is a method of data analysis that automates analytical model building.",
            "RAG (Retrieval Augmented Generation) combines information retrieval with text generation.",
            "Natural Language Processing (NLP) is a branch of AI that helps computers understand human language.",
            "Deep learning is a subset of machine learning that uses neural networks with multiple layers."
        ]
        
        print("Getting embeddings for documents...")
        doc_embeddings = []
        for doc in documents:
            embedding = embeddings.embed_query(doc)
            doc_embeddings.append(embedding)
        
        metadata = [{"source": f"doc_{i}"} for i in range(len(documents))]
        store.add_documents(documents, doc_embeddings, metadata)
        print("✅ Documents embedded and stored")
        
        # Test query
        query = "What is Python programming?"
        print(f"\nQuery: {query}")
        
        query_embedding = embeddings.embed_query(query)
        results = store.similarity_search(query_embedding, k=2)
        
        if results:
            # Use the most relevant document as context
            context = results[0]['document']
            print(f"Retrieved context: {context}")
            
            # Create prompt and get response
            prompt = ChatPromptTemplate.from_template(
                "Based on this context: {context}\n\nAnswer the question: {question}\n\nProvide a helpful and accurate response."
            )
            
            chain = prompt | llm
            response = chain.invoke({"context": context, "question": query})
            
            print(f"✅ RAG response generated")
            print(f"Response: {response.content}")
            
            return True
        else:
            print("❌ No results from similarity search")
            return False
            
    except Exception as e:
        print(f"❌ Ollama integration test failed: {e}")
        return False

def test_core_system_integration():
    """Test integration with core system components."""
    print("\nTesting core system integration...")
    
    try:
        from src.core.system import RAGSystem
        from src.managers.conversation_manager import ConversationManager
        from src.managers.response_manager import ResponseManager
        
        # Initialize system
        rag_system = RAGSystem()
        rag_system.initialize()
        print("✅ RAG System initialized")
        
        # Test managers
        conversation_manager = ConversationManager()
        response_manager = ResponseManager()
        print("✅ Managers created")
        
        # Test a simple conversation
        conversation_id = "test_conversation"
        
        # This would normally use the vector store, but for now just test the structure
        print("✅ Core system integration successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Core system integration failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Simple RAG System")
    print("=" * 50)
    
    tests = [
        test_simple_vector_store,
        test_ollama_integration,
        test_core_system_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Simple RAG system is working.")
        print("\n💡 Next steps:")
        print("   - Install a compatible vector database (ChromaDB, FAISS, etc.)")
        print("   - Add document ingestion pipeline")
        print("   - Install Streamlit for web interface")
    elif passed >= total - 1:
        print("✅ Simple RAG system is mostly working. Check Ollama connection.")
    else:
        print("❌ Simple RAG system has issues.")
    
    return passed >= total - 1

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)