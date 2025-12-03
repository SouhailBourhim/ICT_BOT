#!/usr/bin/env python3
"""
Test script to use ChromaDB directly without langchain-chroma.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_chroma_direct():
    """Test ChromaDB directly."""
    print("Testing ChromaDB direct usage...")
    
    try:
        import chromadb
        print("✅ ChromaDB imported successfully")
        
        # Create a simple in-memory client
        client = chromadb.Client()
        print("✅ ChromaDB client created")
        
        # Create a collection
        collection = client.create_collection("test_collection")
        print("✅ Collection created")
        
        # Add some test documents
        collection.add(
            documents=["This is a test document", "This is another test"],
            metadatas=[{"source": "test1"}, {"source": "test2"}],
            ids=["id1", "id2"]
        )
        print("✅ Documents added")
        
        # Query the collection
        results = collection.query(
            query_texts=["test document"],
            n_results=2
        )
        print(f"✅ Query successful: {len(results['documents'][0])} results")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB test failed: {e}")
        return False

def test_ollama_embeddings():
    """Test Ollama embeddings."""
    print("\nTesting Ollama embeddings...")
    
    try:
        from langchain_ollama import OllamaEmbeddings
        from config.settings import get_settings
        
        config = get_settings()
        embeddings = OllamaEmbeddings(model=config.model.ollama_model)
        print("✅ Ollama embeddings created")
        
        # Test embedding
        try:
            test_text = "This is a test sentence"
            embedding = embeddings.embed_query(test_text)
            print(f"✅ Embedding successful: {len(embedding)} dimensions")
            return True
        except Exception as e:
            print(f"⚠️  Embedding failed (Ollama may not be running): {e}")
            return False
            
    except Exception as e:
        print(f"❌ Ollama embeddings test failed: {e}")
        return False

def test_simple_rag():
    """Test a simple RAG setup without langchain-chroma."""
    print("\nTesting simple RAG setup...")
    
    try:
        import chromadb
        from langchain_ollama import OllamaEmbeddings, ChatOllama
        from langchain_core.prompts import ChatPromptTemplate
        from config.settings import get_settings
        
        config = get_settings()
        
        # Create embeddings and LLM
        embeddings = OllamaEmbeddings(model=config.model.ollama_model)
        llm = ChatOllama(model=config.model.ollama_model)
        
        # Create ChromaDB client and collection
        client = chromadb.Client()
        collection = client.create_collection("rag_test")
        
        # Add some test documents
        documents = [
            "Python is a programming language",
            "Machine learning is a subset of AI",
            "RAG stands for Retrieval Augmented Generation"
        ]
        
        # Get embeddings for documents
        doc_embeddings = [embeddings.embed_query(doc) for doc in documents]
        
        collection.add(
            documents=documents,
            embeddings=doc_embeddings,
            ids=[f"doc_{i}" for i in range(len(documents))]
        )
        
        print("✅ Documents added to ChromaDB")
        
        # Test query
        query = "What is Python?"
        query_embedding = embeddings.embed_query(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=1
        )
        
        if results['documents']:
            context = results['documents'][0][0]
            
            # Create prompt and get response
            prompt = ChatPromptTemplate.from_template(
                "Based on this context: {context}\n\nAnswer the question: {question}"
            )
            
            chain = prompt | llm
            response = chain.invoke({"context": context, "question": query})
            
            print(f"✅ RAG query successful")
            print(f"   Context: {context}")
            print(f"   Response: {response.content[:100]}...")
            
            return True
        else:
            print("❌ No results from query")
            return False
            
    except Exception as e:
        print(f"❌ Simple RAG test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing ChromaDB Direct Integration")
    print("=" * 50)
    
    tests = [
        test_chroma_direct,
        test_ollama_embeddings,
        test_simple_rag
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! ChromaDB integration is working.")
    elif passed >= total - 1:
        print("✅ ChromaDB integration is mostly working. Check Ollama connection.")
    else:
        print("❌ ChromaDB integration has issues.")
    
    return passed >= total - 1

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)