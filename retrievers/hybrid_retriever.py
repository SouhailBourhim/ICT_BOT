"""
Hybrid retriever that combines semantic and keyword search with ChromaDB integration.
"""
import os
import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

from models.base import ProcessedChunk, RetrievalResult, ContentType
from retrievers.interfaces import HybridRetrieverInterface, SemanticRetrieverInterface
from retrievers.bm25_retriever import BM25Retriever
from retrievers.reranker import HybridReRanker

logger = logging.getLogger(__name__)


class SemanticRetriever(SemanticRetrieverInterface):
    """Semantic retriever using ChromaDB vector database."""
    
    def __init__(self, chroma_path: str = "chroma", embedding_model: str = "llama3"):
        """Initialize semantic retriever.
        
        Args:
            chroma_path: Path to ChromaDB directory
            embedding_model: Embedding model name
        """
        self.chroma_path = chroma_path
        self.embedding_model = embedding_model
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.db = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize ChromaDB connection."""
        if os.path.exists(self.chroma_path):
            self.db = Chroma(
                persist_directory=self.chroma_path,
                embedding_function=self.embeddings
            )
            logger.info(f"Connected to ChromaDB at {self.chroma_path}")
        else:
            logger.warning(f"ChromaDB not found at {self.chroma_path}")
    
    def semantic_search(self, query: str, k: int) -> List[RetrievalResult]:
        """Perform semantic similarity search.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of semantic search results
        """
        if not self.db:
            logger.warning("ChromaDB not initialized")
            return []
        
        try:
            # Perform similarity search
            results = self.db.similarity_search_with_score(query, k=k)
            
            # Convert to RetrievalResult objects
            retrieval_results = []
            for doc, score in results:
                # Convert LangChain document to ProcessedChunk
                chunk = self._langchain_doc_to_chunk(doc)
                
                result = RetrievalResult(
                    chunk=chunk,
                    score=float(score),
                    retrieval_method="semantic_vector",
                    metadata={
                        "similarity_score": float(score),
                        "embedding_model": self.embedding_model,
                        "query": query
                    }
                )
                retrieval_results.append(result)
            
            logger.info(f"Semantic search returned {len(retrieval_results)} results")
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def _langchain_doc_to_chunk(self, doc) -> ProcessedChunk:
        """Convert LangChain document to ProcessedChunk.
        
        Args:
            doc: LangChain document
            
        Returns:
            ProcessedChunk object
        """
        metadata = doc.metadata
        
        # Extract hierarchical context
        hierarchical_context = []
        if 'hierarchical_context' in metadata:
            try:
                hierarchical_context = json.loads(metadata['hierarchical_context'])
            except (json.JSONDecodeError, TypeError):
                hierarchical_context = []
        
        # Determine content type
        content_type = ContentType.TEXT
        if 'content_type' in metadata:
            try:
                content_type = ContentType(metadata['content_type'])
            except ValueError:
                content_type = ContentType.TEXT
        
        # Create chunk ID if not present
        chunk_id = metadata.get('chunk_id', f"{metadata.get('document_id', 'unknown')}_{hash(doc.page_content)}")
        
        return ProcessedChunk(
            chunk_id=chunk_id,
            document_id=metadata.get('document_id', 'unknown'),
            content=doc.page_content,
            content_type=content_type,
            hierarchical_context=hierarchical_context,
            page_number=metadata.get('page_number', 0),
            position_in_document=metadata.get('position_in_document', 0.0),
            metadata=metadata
        )
    
    def setup_index(self, chunks: List[ProcessedChunk]) -> None:
        """Set up the semantic search index (ChromaDB handles this)."""
        # ChromaDB index is managed by the ingestion pipeline
        pass
    
    def retrieve(self, query: str, filters: Dict[str, Any], k: int = 10) -> List[RetrievalResult]:
        """Retrieve with optional metadata filters.
        
        Args:
            query: Search query
            filters: Metadata filters
            k: Number of results
            
        Returns:
            Filtered retrieval results
        """
        if not self.db:
            return []
        
        try:
            # Build ChromaDB filter from our filters
            chroma_filter = self._build_chroma_filter(filters)
            
            # Perform filtered search
            if chroma_filter:
                results = self.db.similarity_search_with_score(
                    query, k=k, filter=chroma_filter
                )
            else:
                results = self.db.similarity_search_with_score(query, k=k)
            
            # Convert results
            retrieval_results = []
            for doc, score in results:
                chunk = self._langchain_doc_to_chunk(doc)
                result = RetrievalResult(
                    chunk=chunk,
                    score=float(score),
                    retrieval_method="semantic_vector_filtered",
                    metadata={
                        "similarity_score": float(score),
                        "filters_applied": filters,
                        "query": query
                    }
                )
                retrieval_results.append(result)
            
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Error in filtered semantic search: {e}")
            return []
    
    def _build_chroma_filter(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build ChromaDB filter from our filter format.
        
        Args:
            filters: Our filter format
            
        Returns:
            ChromaDB compatible filter or None
        """
        if not filters:
            return None
        
        chroma_filter = {}
        
        for key, value in filters.items():
            if key == "content_type":
                chroma_filter["content_type"] = {"$eq": value}
            elif key == "document_id":
                chroma_filter["document_id"] = {"$eq": value}
            elif key == "page_number":
                if isinstance(value, dict):
                    if "min" in value and "max" in value:
                        chroma_filter["page_number"] = {
                            "$gte": value["min"],
                            "$lte": value["max"]
                        }
                    elif "min" in value:
                        chroma_filter["page_number"] = {"$gte": value["min"]}
                    elif "max" in value:
                        chroma_filter["page_number"] = {"$lte": value["max"]}
                else:
                    chroma_filter["page_number"] = {"$eq": value}
            else:
                # For other metadata fields
                chroma_filter[key] = {"$eq": value}
        
        return chroma_filter if chroma_filter else None


class HybridRetriever(HybridRetrieverInterface):
    """Hybrid retriever combining semantic and keyword search."""
    
    def __init__(self, 
                 chroma_path: str = "chroma",
                 metadata_db_path: str = "metadata.db",
                 embedding_model: str = "llama3",
                 semantic_weight: float = 0.6,
                 keyword_weight: float = 0.4):
        """Initialize hybrid retriever.
        
        Args:
            chroma_path: Path to ChromaDB directory
            metadata_db_path: Path to metadata SQLite database
            embedding_model: Embedding model name
            semantic_weight: Weight for semantic search results
            keyword_weight: Weight for keyword search results
        """
        self.chroma_path = chroma_path
        self.metadata_db_path = metadata_db_path
        self.embedding_model = embedding_model
        
        # Initialize retrievers
        self.semantic_retriever = SemanticRetriever(chroma_path, embedding_model)
        self.keyword_retriever = BM25Retriever()
        self.reranker = HybridReRanker(
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight
        )
        
        # Initialize BM25 index from stored chunks
        self._initialize_keyword_index()
    
    def _initialize_keyword_index(self):
        """Initialize BM25 index from stored chunk data."""
        try:
            chunks = self._load_chunks_from_metadata_db()
            if chunks:
                self.keyword_retriever.setup_index(chunks)
                logger.info(f"Initialized BM25 index with {len(chunks)} chunks")
            else:
                logger.warning("No chunks found in metadata database")
        except Exception as e:
            logger.error(f"Error initializing keyword index: {e}")
    
    def _load_chunks_from_metadata_db(self) -> List[ProcessedChunk]:
        """Load chunks from metadata database.
        
        Returns:
            List of ProcessedChunk objects
        """
        if not os.path.exists(self.metadata_db_path):
            logger.warning(f"Metadata database not found: {self.metadata_db_path}")
            return []
        
        chunks = []
        try:
            conn = sqlite3.connect(self.metadata_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT chunk_id, document_id, content, content_type, 
                       hierarchical_context, page_number, position_in_document, metadata
                FROM chunks
            """)
            
            for row in cursor.fetchall():
                chunk_id, document_id, content, content_type, hierarchical_context, \
                page_number, position_in_document, metadata_json = row
                
                # Parse JSON fields
                try:
                    hierarchical_context = json.loads(hierarchical_context) if hierarchical_context else []
                    metadata = json.loads(metadata_json) if metadata_json else {}
                except json.JSONDecodeError:
                    hierarchical_context = []
                    metadata = {}
                
                # Create ProcessedChunk
                chunk = ProcessedChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    content=content,
                    content_type=ContentType(content_type),
                    hierarchical_context=hierarchical_context,
                    page_number=page_number,
                    position_in_document=position_in_document,
                    metadata=metadata
                )
                chunks.append(chunk)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error loading chunks from metadata DB: {e}")
        
        return chunks
    
    def retrieve(self, query: str, filters: Dict[str, Any], k: int = 10) -> List[RetrievalResult]:
        """Perform hybrid retrieval combining semantic and keyword search.
        
        Args:
            query: Search query
            filters: Metadata filters
            k: Number of results to return
            
        Returns:
            Hybrid search results
        """
        # Determine search strategy based on query characteristics
        search_strategy = self._determine_search_strategy(query)
        
        if search_strategy == "semantic_only":
            return self.semantic_retriever.retrieve(query, filters, k)
        elif search_strategy == "keyword_only":
            return self.keyword_retriever.retrieve(query, filters, k)
        else:
            # Hybrid search
            return self._perform_hybrid_search(query, filters, k)
    
    def _determine_search_strategy(self, query: str) -> str:
        """Determine optimal search strategy based on query characteristics.
        
        Args:
            query: Search query
            
        Returns:
            Search strategy: 'semantic_only', 'keyword_only', or 'hybrid'
        """
        query_lower = query.lower()
        
        # Use keyword search for very specific technical terms
        technical_indicators = [
            "tcp/ip", "http", "https", "api", "json", "xml",
            "algorithm", "function", "method", "class", "variable"
        ]
        
        if any(indicator in query_lower for indicator in technical_indicators):
            if len(query.split()) <= 3:  # Short technical queries
                return "keyword_only"
        
        # Use semantic search for conceptual queries
        conceptual_indicators = [
            "explain", "what is", "how does", "why", "concept", "theory",
            "understand", "meaning", "definition", "overview"
        ]
        
        if any(indicator in query_lower for indicator in conceptual_indicators):
            return "semantic_only"
        
        # Default to hybrid for most queries
        return "hybrid"
    
    def _perform_hybrid_search(self, query: str, filters: Dict[str, Any], k: int) -> List[RetrievalResult]:
        """Perform hybrid search combining both methods.
        
        Args:
            query: Search query
            filters: Metadata filters
            k: Number of results to return
            
        Returns:
            Fused and re-ranked results
        """
        # Get results from both methods (get more for better fusion)
        search_k = min(k * 2, 20)  # Get up to 2x results for fusion
        
        semantic_results = self.semantic_retriever.retrieve(query, filters, search_k)
        keyword_results = self.keyword_retriever.retrieve(query, filters, search_k)
        
        logger.info(f"Hybrid search: {len(semantic_results)} semantic + "
                   f"{len(keyword_results)} keyword results")
        
        # Fuse results using RRF
        fused_results = self.reranker.fuse_results_rrf(semantic_results, keyword_results)
        
        # Re-rank with enhanced scoring
        reranked_results = self.reranker.rerank(query, fused_results)
        
        # Apply diversity if we have many results
        if len(reranked_results) > k:
            final_results = self.reranker.diversify_results(reranked_results, max_results=k)
        else:
            final_results = reranked_results[:k]
        
        logger.info(f"Hybrid search final: {len(final_results)} results")
        return final_results
    
    def fuse_results(self, semantic_results: List[RetrievalResult], 
                    keyword_results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Fuse results from multiple retrieval methods.
        
        Args:
            semantic_results: Results from semantic search
            keyword_results: Results from keyword search
            
        Returns:
            Fused results
        """
        return self.reranker.fuse_results_rrf(semantic_results, keyword_results)
    
    def setup_index(self, chunks: List[ProcessedChunk]) -> None:
        """Set up retrieval indexes.
        
        Args:
            chunks: List of processed chunks
        """
        # Set up BM25 index
        self.keyword_retriever.setup_index(chunks)
        
        # Semantic index is handled by ChromaDB through ingestion pipeline
        logger.info("Hybrid retriever indexes updated")
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval system statistics.
        
        Returns:
            Dictionary with system statistics
        """
        stats = {
            "semantic_retriever": {
                "chroma_path": self.chroma_path,
                "embedding_model": self.embedding_model,
                "available": self.semantic_retriever.db is not None
            },
            "keyword_retriever": {
                "index_size": len(self.keyword_retriever.chunks),
                "inverted_index_terms": len(self.keyword_retriever.inverted_index),
                "available": self.keyword_retriever.bm25_index is not None
            },
            "reranker": {
                "semantic_weight": self.reranker.semantic_weight,
                "keyword_weight": self.reranker.keyword_weight,
                "rrf_k": self.reranker.rrf_k
            }
        }
        
        # Add database statistics if available
        try:
            if os.path.exists(self.metadata_db_path):
                conn = sqlite3.connect(self.metadata_db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM documents")
                document_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cursor.fetchone()[0]
                
                stats["metadata_database"] = {
                    "path": self.metadata_db_path,
                    "documents": document_count,
                    "chunks": chunk_count
                }
                
                conn.close()
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
        
        return stats
    
    def refresh_indexes(self):
        """Refresh all retrieval indexes from stored data."""
        logger.info("Refreshing retrieval indexes...")
        
        # Refresh semantic retriever connection
        self.semantic_retriever._initialize_db()
        
        # Refresh keyword index
        self._initialize_keyword_index()
        
        logger.info("Retrieval indexes refreshed")


def create_hybrid_search_demo():
    """Create a demo script for testing hybrid search."""
    demo_script = '''#!/usr/bin/env python3
"""
Demo script for testing hybrid retrieval system.
"""
import sys
from retrievers.hybrid_retriever import HybridRetriever


def main():
    # Initialize hybrid retriever
    retriever = HybridRetriever()
    
    # Get system stats
    stats = retriever.get_retrieval_stats()
    print("🔍 Hybrid Retrieval System Status:")
    print(f"   Semantic: {'✅' if stats['semantic_retriever']['available'] else '❌'}")
    print(f"   Keyword: {'✅' if stats['keyword_retriever']['available'] else '❌'}")
    print(f"   Documents: {stats.get('metadata_database', {}).get('documents', 0)}")
    print(f"   Chunks: {stats.get('metadata_database', {}).get('chunks', 0)}")
    
    if not (stats['semantic_retriever']['available'] and stats['keyword_retriever']['available']):
        print("\\n❌ Retrieval system not fully initialized.")
        print("Please run the ingestion pipeline first: python ingest_enhanced.py")
        return
    
    # Test queries
    test_queries = [
        "wireless communication systems",
        "TCP/IP protocol implementation",
        "Shannon capacity formula",
        "BM25 algorithm",
        "Rayleigh fading channels"
    ]
    
    print("\\n🧪 Testing hybrid search with sample queries...")
    
    for query in test_queries:
        print(f"\\n📝 Query: '{query}'")
        
        try:
            results = retriever.retrieve(query, {}, k=3)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"   {i}. [{result.retrieval_method}] Score: {result.score:.3f}")
                    print(f"      {result.chunk.content[:100]}...")
                    if result.chunk.hierarchical_context:
                        print(f"      Context: {' > '.join(result.chunk.hierarchical_context)}")
            else:
                print("   No results found")
                
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\\n✅ Demo completed!")


if __name__ == "__main__":
    main()
'''
    
    with open("demo_hybrid_search.py", "w") as f:
        f.write(demo_script)
    
    print("Hybrid search demo created: demo_hybrid_search.py")


if __name__ == "__main__":
    create_hybrid_search_demo()