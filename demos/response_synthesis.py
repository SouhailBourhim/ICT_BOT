#!/usr/bin/env python3
"""
Demo script for enhanced response generation and multi-source synthesis.
"""
import sys
from datetime import datetime
from typing import List

# Add project root to path
sys.path.append('.')

from src.models.base import (
    ProcessedChunk, RetrievalResult, DocumentMetadata, ContentType,
    ConversationContext, Message
)
from src.managers.response_manager import ResponseManager
from src.managers.synthesis_manager import SynthesisManager


def create_sample_chunks() -> List[ProcessedChunk]:
    """Create sample chunks for demonstration."""
    
    # Metadata for different documents
    tcp_metadata = {
        "title": "Cours TCP/IP - Protocoles Fiables",
        "course_module": "Réseaux Informatiques",
        "document_type": "pdf",
        "creation_date": datetime(2023, 9, 1)
    }
    
    udp_metadata = {
        "title": "Guide UDP - Protocoles Rapides",
        "course_module": "Réseaux Informatiques", 
        "document_type": "pdf",
        "creation_date": datetime(2023, 8, 15)
    }
    
    old_metadata = {
        "title": "Ancien Manuel de Réseaux",
        "course_module": "Réseaux",
        "document_type": "txt",
        "creation_date": datetime(2020, 1, 1)
    }
    
    chunks = [
        # TCP chunks - reliable information
        ProcessedChunk(
            chunk_id="tcp_chunk_1",
            document_id="tcp_doc",
            content="TCP (Transmission Control Protocol) est un protocole de transport fiable qui garantit la livraison ordonnée des données. Il utilise un mécanisme d'accusé de réception pour s'assurer que tous les paquets arrivent à destination.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 3", "Section 3.1", "TCP Basics"],
            page_number=45,
            position_in_document=0.3,
            metadata=tcp_metadata
        ),
        
        ProcessedChunk(
            chunk_id="tcp_chunk_2", 
            document_id="tcp_doc",
            content="Le protocole TCP implémente un contrôle de flux et un contrôle de congestion. Par exemple, la fenêtre glissante permet de réguler le débit de transmission selon la capacité du récepteur.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 3", "Section 3.2", "Flow Control"],
            page_number=47,
            position_in_document=0.32,
            metadata=tcp_metadata
        ),
        
        # UDP chunks - different perspective
        ProcessedChunk(
            chunk_id="udp_chunk_1",
            document_id="udp_doc", 
            content="UDP (User Datagram Protocol) est un protocole sans connexion qui privilégie la rapidité. Contrairement à TCP, UDP ne garantit pas la livraison des données mais offre une latence plus faible.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 2", "Section 2.1", "UDP Overview"],
            page_number=23,
            position_in_document=0.2,
            metadata=udp_metadata
        ),
        
        # Potentially conflicting information from old source
        ProcessedChunk(
            chunk_id="old_chunk_1",
            document_id="old_doc",
            content="TCP est probablement fiable dans la plupart des cas, mais il peut parfois perdre des paquets selon certaines études anciennes.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 1"],
            page_number=10,
            position_in_document=0.1,
            metadata=old_metadata
        ),
        
        # High-quality technical chunk
        ProcessedChunk(
            chunk_id="technical_chunk_1",
            document_id="tcp_doc",
            content="Selon la RFC 793, TCP utilise un numéro de séquence de 32 bits pour ordonner les segments. Le mécanisme de retransmission automatique (ARQ) assure la fiabilité en retransmettant les segments perdus après expiration du timeout.",
            content_type=ContentType.TEXT,
            hierarchical_context=["Chapitre 3", "Section 3.3", "Technical Details"],
            page_number=52,
            position_in_document=0.35,
            metadata=tcp_metadata
        )
    ]
    
    return chunks


def create_sample_retrieval_results(chunks: List[ProcessedChunk]) -> List[RetrievalResult]:
    """Create sample retrieval results."""
    return [
        RetrievalResult(
            chunk=chunks[0],
            score=0.92,
            retrieval_method="semantic",
            metadata={"query_similarity": 0.92, "bm25_score": 0.85}
        ),
        RetrievalResult(
            chunk=chunks[1], 
            score=0.88,
            retrieval_method="hybrid",
            metadata={"query_similarity": 0.85, "bm25_score": 0.91}
        ),
        RetrievalResult(
            chunk=chunks[2],
            score=0.75,
            retrieval_method="semantic", 
            metadata={"query_similarity": 0.75, "bm25_score": 0.65}
        ),
        RetrievalResult(
            chunk=chunks[3],
            score=0.60,
            retrieval_method="keyword",
            metadata={"query_similarity": 0.55, "bm25_score": 0.70}
        ),
        RetrievalResult(
            chunk=chunks[4],
            score=0.95,
            retrieval_method="semantic",
            metadata={"query_similarity": 0.95, "bm25_score": 0.88}
        )
    ]


def create_conversation_context() -> ConversationContext:
    """Create sample conversation context."""
    messages = [
        Message(
            message_id="msg_1",
            role="user",
            content="Qu'est-ce que TCP?",
            timestamp=datetime.now(),
            sources=[],
            confidence=1.0
        ),
        Message(
            message_id="msg_2", 
            role="assistant",
            content="TCP est un protocole de transport fiable utilisé sur Internet.",
            timestamp=datetime.now(),
            sources=["tcp_doc"],
            confidence=0.9
        )
    ]
    
    return ConversationContext(
        conversation_id="demo_conv_1",
        recent_messages=messages,
        summary="Discussion sur les protocoles de transport TCP et UDP",
        relevant_topics=["TCP", "UDP", "protocoles", "fiabilité"],
        context_tokens=150
    )


def demo_response_generation():
    """Demonstrate enhanced response generation with citations."""
    print("=" * 80)
    print("DEMO: Enhanced Response Generation with Citations")
    print("=" * 80)
    
    # Create sample data
    chunks = create_sample_chunks()
    retrieval_results = create_sample_retrieval_results(chunks)
    conversation = create_conversation_context()
    
    # Initialize response manager
    response_manager = ResponseManager()
    
    # Test query
    query = "Comment TCP assure-t-il la fiabilité des transmissions?"
    
    print(f"\n📝 Query: {query}")
    print(f"📊 Retrieved {len(retrieval_results)} sources")
    
    try:
        # Generate response with citations
        print("\n🔄 Generating response with citations...")
        response = response_manager.generate_response(query, retrieval_results, conversation)
        
        print(f"\n✅ Response generated successfully!")
        print(f"📈 Confidence: {response.confidence:.2f}")
        print(f"📚 Citations: {len(response.citations)}")
        
        print(f"\n📄 Response Content:")
        print("-" * 50)
        print(response.content)
        
        print(f"\n📖 Citations:")
        print("-" * 30)
        for i, citation in enumerate(response.citations, 1):
            print(f"{i}. {citation}")
        
        print(f"\n📊 Generation Metadata:")
        print("-" * 40)
        for key, value in response.generation_metadata.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"❌ Error in response generation: {e}")


def demo_multi_source_synthesis():
    """Demonstrate multi-source information synthesis."""
    print("\n" + "=" * 80)
    print("DEMO: Multi-Source Information Synthesis")
    print("=" * 80)
    
    # Create sample data
    chunks = create_sample_chunks()
    retrieval_results = create_sample_retrieval_results(chunks)
    
    # Initialize synthesis manager
    synthesis_manager = SynthesisManager()
    
    print(f"\n📊 Analyzing {len(retrieval_results)} sources for synthesis...")
    
    try:
        # Perform synthesis
        print("\n🔄 Performing multi-source synthesis...")
        synthesis_result = synthesis_manager.synthesize_sources(retrieval_results)
        
        print(f"\n✅ Synthesis completed!")
        print(f"📈 Synthesis Confidence: {synthesis_result.synthesis_confidence:.2f}")
        print(f"⚠️  Conflicts Detected: {len(synthesis_result.detected_conflicts)}")
        print(f"📚 Sources Analyzed: {len(synthesis_result.source_reliability)}")
        
        print(f"\n📄 Synthesized Content:")
        print("-" * 50)
        print(synthesis_result.synthesized_content)
        
        print(f"\n📊 Source Reliability Scores:")
        print("-" * 40)
        for reliability in synthesis_result.source_reliability:
            print(f"  {reliability.source_id}: {reliability.reliability_score:.2f}")
            print(f"    Factors: {reliability.factors}")
        
        if synthesis_result.detected_conflicts:
            print(f"\n⚠️  Detected Conflicts:")
            print("-" * 30)
            for conflict in synthesis_result.detected_conflicts:
                print(f"  Type: {conflict.conflict_type.value}")
                print(f"  Description: {conflict.description}")
                print(f"  Confidence: {conflict.confidence:.2f}")
                print(f"  Sources: {conflict.source_ids}")
                print()
        
        print(f"\n📋 Methodology Notes:")
        print("-" * 30)
        print(synthesis_result.methodology_notes)
        
    except Exception as e:
        print(f"❌ Error in synthesis: {e}")


def demo_integrated_workflow():
    """Demonstrate integrated response generation with synthesis."""
    print("\n" + "=" * 80)
    print("DEMO: Integrated Response Generation + Synthesis")
    print("=" * 80)
    
    # Create sample data
    chunks = create_sample_chunks()
    retrieval_results = create_sample_retrieval_results(chunks)
    conversation = create_conversation_context()
    
    # Initialize response manager (which includes synthesis manager)
    response_manager = ResponseManager()
    
    query = "Comparez TCP et UDP en termes de fiabilité et performance"
    
    print(f"\n📝 Complex Query: {query}")
    print(f"📊 Retrieved {len(retrieval_results)} sources from multiple documents")
    
    try:
        # Generate comprehensive response
        print("\n🔄 Generating comprehensive response...")
        response = response_manager.generate_response(query, retrieval_results, conversation)
        
        print(f"\n✅ Response generated!")
        print(f"📈 Confidence: {response.confidence:.2f}")
        
        print(f"\n📄 Response with Citations:")
        print("-" * 50)
        print(response.content)
        
        # Also demonstrate synthesis
        print(f"\n🔄 Performing advanced synthesis...")
        synthesis = response_manager.synthesize_sources(retrieval_results)
        
        print(f"\n📊 Advanced Synthesis Result:")
        print("-" * 50)
        print(synthesis)
        
    except Exception as e:
        print(f"❌ Error in integrated workflow: {e}")


def main():
    """Run all demonstrations."""
    print("🚀 Enhanced Response Generation and Synthesis Demo")
    print("This demo showcases the advanced capabilities of the RAG system")
    
    try:
        # Demo 1: Response generation with citations
        demo_response_generation()
        
        # Demo 2: Multi-source synthesis
        demo_multi_source_synthesis()
        
        # Demo 3: Integrated workflow
        demo_integrated_workflow()
        
        print("\n" + "=" * 80)
        print("✅ All demos completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()