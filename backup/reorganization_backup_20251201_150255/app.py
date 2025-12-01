import streamlit as st

# Configure Streamlit page FIRST - before any other Streamlit commands
st.set_page_config(
    page_title="Assistant Smart ICT (Enhanced)",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import traceback

# Import enhanced system components
from core.system import RAGSystem
from config.settings import get_settings
from managers.conversation_manager import ConversationManager
from managers.response_manager import ResponseManager
from models.base import Message
from managers.query_enhancer import QueryEnhancer
from managers.analytics_manager import AnalyticsManager
from retrievers.hybrid_retriever import HybridRetriever
from ui.components import UIComponentManager
# Removed filters - not needed
from utils.error_handler import ErrorHandler
from utils.health_monitor import HealthMonitor

# Backward compatibility imports
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# Initialize system components
@st.cache_resource
def initialize_system():
    """Initialize the enhanced RAG system with caching."""
    try:
        # Get configuration
        config = get_settings()
        
        # Initialize core system
        rag_system = RAGSystem()
        rag_system.initialize()
        
        # Initialize managers
        conversation_manager = ConversationManager()
        response_manager = ResponseManager()
        query_enhancer = QueryEnhancer()
        analytics_manager = AnalyticsManager()
        hybrid_retriever = HybridRetriever()
        error_handler = ErrorHandler()
        health_monitor = HealthMonitor()
        
        return {
            "rag_system": rag_system,
            "conversation_manager": conversation_manager,
            "response_manager": response_manager,
            "query_enhancer": query_enhancer,
            "analytics_manager": analytics_manager,
            "hybrid_retriever": hybrid_retriever,
            "error_handler": error_handler,
            "health_monitor": health_monitor,
            "config": config
        }
    except Exception as e:
        # Don't use st.error in cached function - just return None and handle in main
        print(f"Failed to initialize system: {e}")
        return None

def get_vectorstore_legacy():
    """Legacy function for backward compatibility."""
    config = get_settings()
    embeddings = OllamaEmbeddings(model=config.model.ollama_model)
    db = Chroma(persist_directory=config.database.chroma_path, embedding_function=embeddings)
    return db

def main():
    # Initialize system
    system_components = initialize_system()
    if not system_components:
        st.error("Failed to initialize system. Please check logs.")
        return
    
    config = system_components["config"]
    
    # Initialize UI components
    ui_manager = UIComponentManager()
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())
    if "use_enhanced_mode" not in st.session_state:
        st.session_state.use_enhanced_mode = True
    
    # Main header
    st.title("🎓 Assistant Virtuel - Smart ICT (Enhanced)")
    st.subheader("INPT - Institut National des Postes et Télécommunications")
    
    # System status indicator
    with st.sidebar:
        st.markdown("### 🔧 System Status")
        health_status = system_components["health_monitor"].get_health_summary()
        
        if health_status.get("overall_status") == "healthy":
            st.success("✅ System Healthy")
        else:
            st.warning("⚠️ System Issues Detected")
        
        # Mode toggle
        st.markdown("### ⚙️ Mode Selection")
        use_enhanced = st.checkbox(
            "Enhanced Mode", 
            value=st.session_state.use_enhanced_mode,
            help="Use enhanced features (conversation memory, hybrid search, etc.)"
        )
        st.session_state.use_enhanced_mode = use_enhanced
        
        if not use_enhanced:
            st.info("💡 Running in legacy compatibility mode")
    
    # No filters needed - simplified interface
    active_filters = {}
    
    # Check system availability
    try:
        if st.session_state.use_enhanced_mode:
            # Use enhanced system
            retriever = system_components["hybrid_retriever"]
            conversation_manager = system_components["conversation_manager"]
            response_manager = system_components["response_manager"]
            query_enhancer = system_components["query_enhancer"]
            analytics_manager = system_components["analytics_manager"]
        else:
            # Use legacy system for backward compatibility
            db = get_vectorstore_legacy()
            retriever = None
            conversation_manager = None
            response_manager = None
            query_enhancer = None
            analytics_manager = None
    except Exception as e:
        st.error(f"Erreur : {e}")
        st.info("Trying legacy mode...")
        st.session_state.use_enhanced_mode = False
        try:
            db = get_vectorstore_legacy()
        except Exception:
            st.error("Erreur : La base de données est introuvable. Avez-vous lancé 'ingest.py' ?")
            return

    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Enhanced input with auto-complete
        st.markdown("### 💬 Posez votre question")
        prompt = ui_manager.render_enhanced_input("main_query")
        
        # Simplified - no search enhancements needed
        
        # Chat interface
        if prompt:
            try:
                if st.session_state.use_enhanced_mode:
                    # Enhanced mode processing
                    process_enhanced_query(
                        prompt, system_components, ui_manager
                    )
                else:
                    # Legacy mode processing
                    process_legacy_query(
                        prompt, db, ui_manager, config
                    )
                    
            except Exception as e:
                error_handler = system_components.get("error_handler")
                if error_handler:
                    error_info = error_handler.handle_error(e, {"query": prompt})
                    if error_info:
                        st.error(f"Erreur: {error_info.message}")
                        if error_info.recovery_strategy:
                            st.info(f"💡 Stratégie de récupération: {error_info.recovery_strategy.value}")
                    else:
                        st.error(f"Une erreur est survenue : {e}")
                else:
                    st.error(f"Une erreur est survenue : {e}")
                    st.info("Assurez-vous que Ollama est lancé en arrière-plan.")

def process_enhanced_query(prompt: str, system_components: Dict, ui_manager: UIComponentManager):
    """Process query using enhanced system components."""
    conversation_manager = system_components["conversation_manager"]
    response_manager = system_components["response_manager"]
    query_enhancer = system_components["query_enhancer"]
    analytics_manager = system_components["analytics_manager"]
    hybrid_retriever = system_components["hybrid_retriever"]
    
    # No filters in enhanced mode
    active_filters = {}
    
    # Get conversation context
    conversation_context = conversation_manager.get_context(
        st.session_state.conversation_id,
        max_tokens=2000
    )
    
    # Enhance query
    enhanced_query = query_enhancer.enhance_query(prompt, conversation_context)
    
    # Use enhanced query directly - no filters needed
    query_to_use = enhanced_query.corrected_query
    
    # Display User Message
    # Create user message for display (dictionary for Streamlit)
    user_message_display = {
        "role": "user", 
        "content": prompt,
        "timestamp": datetime.now().isoformat(),
        "enhanced_query": enhanced_query.corrected_query if enhanced_query.corrected_query != prompt else None
    }
    
    # Create user message for conversation manager (Message object)
    user_message_obj = Message(
        message_id=str(uuid.uuid4()),
        role="user",
        content=prompt,
        timestamp=datetime.now(),
        sources=[],
        confidence=1.0
    )
    
    st.session_state.messages.append(user_message_display)
    conversation_manager.add_message(st.session_state.conversation_id, user_message_obj)
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if enhanced_query.corrected_query != prompt:
            st.caption(f"🔍 Enhanced: {enhanced_query.corrected_query}")
        if active_filters:
            st.caption(f"🔍 Filtres appliqués: {', '.join(active_filters.keys())}")

    # Generate Answer
    with st.chat_message("assistant"):
        with st.spinner("Recherche dans les cours..."):
            # Retrieve relevant documents
            retrieval_results = hybrid_retriever.retrieve(
                query_to_use,
                filters={},  # No filters needed
                k=system_components["config"].retrieval.default_k
            )
            
            # Generate response
            response_result = response_manager.generate_response(
                prompt, retrieval_results, conversation_context
            )
            
            # Enhanced response rendering
            ui_manager.render_enhanced_response(response_result.response)
            
            # Display citations if available
            if response_result.citations:
                with st.expander("📚 Sources", expanded=False):
                    for citation in response_result.citations:
                        st.markdown(f"- **{citation.document_title}** (Page {citation.page_number})")
                        if citation.relevance_score:
                            st.caption(f"Relevance: {citation.relevance_score:.2f}")
            
            # Add response feedback
            response_id = str(uuid.uuid4())
            feedback = ui_manager.add_response_feedback(response_id)
            
            # Save Assistant Message
            # Create assistant message for display (dictionary for Streamlit)
            assistant_message_display = {
                "role": "assistant", 
                "content": response_result.response,
                "timestamp": datetime.now().isoformat(),
                "response_id": response_id,
                "sources": [r.document_id for r in retrieval_results],
                "citations": response_result.citations,
                "confidence": response_result.confidence_score,
                "feedback": feedback
            }
            
            # Create assistant message for conversation manager (Message object)
            assistant_message_obj = Message(
                message_id=response_id,
                role="assistant",
                content=response_result.response,
                timestamp=datetime.now(),
                sources=[r.document_id for r in retrieval_results],
                confidence=response_result.confidence_score
            )
            
            st.session_state.messages.append(assistant_message_display)
            conversation_manager.add_message(st.session_state.conversation_id, assistant_message_obj)
            
            # Log analytics
            analytics_manager.log_query_response(
                query=prompt,
                response=response_result.response,
                retrieval_results=retrieval_results,
                response_time=response_result.processing_time,
                confidence=response_result.confidence_score
            )

def process_legacy_query(prompt: str, db: Chroma, ui_manager: UIComponentManager, config):
    """Process query using legacy system for backward compatibility."""
    # Legacy prompt template
    PROMPT_TEMPLATE = """
    Tu es un assistant éducatif pour les étudiants en Smart ICT à l'INPT.
    Réponds à la question suivante en te basant **uniquement** sur le contexte fourni ci-dessous.
    Si la réponse ne se trouve pas dans le contexte, dis poliment que tu ne sais pas. N'invente pas d'informations.

    <contexte>
    {context}
    </contexte>

    Question de l'étudiant : {input}
    """
    
    # Use prompt directly - no filters needed
    
    # Display User Message
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt,
        "timestamp": datetime.now().isoformat(),
        "filters": active_filters
    })
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if active_filters:
            st.caption(f"🔍 Filtres appliqués: {', '.join(active_filters.keys())}")

    # Generate Answer
    with st.chat_message("assistant"):
        with st.spinner("Recherche dans les cours..."):
            # Setup LLM and Retriever
            llm = ChatOllama(model=config.model.ollama_model)
            
            # Apply filters to retriever if available
            search_kwargs = {"k": config.retrieval.default_k}
            if enhanced_query.filters:
                search_kwargs["filter"] = enhanced_query.filters
            
            retriever = db.as_retriever(search_kwargs=search_kwargs)
            
            # Create Chains
            prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
            question_answer_chain = create_stuff_documents_chain(llm, prompt_template)
            rag_chain = create_retrieval_chain(retriever, question_answer_chain)
            
            # Run Chain
            response = rag_chain.invoke({"input": prompt})
            answer = response["answer"]
            
            # Enhanced response rendering
            ui_manager.render_enhanced_response(answer)
            
            # Add response feedback
            response_id = str(uuid.uuid4())
            feedback = ui_manager.add_response_feedback(response_id)
            
            # Save Assistant Message
            st.session_state.messages.append({
                "role": "assistant", 
                "content": answer,
                "timestamp": datetime.now().isoformat(),
                "response_id": response_id,
                "sources": response.get("context", []),
                "feedback": feedback
            })
    
    with col2:
        # Enhanced conversation management
        st.markdown("### 📜 Conversation Management")
        
        col2a, col2b = st.columns(2)
        with col2a:
            if st.button("🗑️ New Chat", key="new_conversation"):
                if st.session_state.use_enhanced_mode and conversation_manager:
                    # Save current conversation before starting new one
                    conversation_manager.end_conversation(st.session_state.conversation_id)
                
                st.session_state.messages = []
                st.session_state.conversation_id = str(uuid.uuid4())
                from utils.streamlit_compat import safe_rerun
                safe_rerun()
        
        with col2b:
            if st.session_state.use_enhanced_mode and conversation_manager:
                if st.button("💾 Save Chat", key="save_conversation"):
                    conversation_manager.save_conversation(st.session_state.conversation_id)
                    st.success("Conversation saved!")
        
        # Enhanced conversation history
        if st.session_state.use_enhanced_mode and conversation_manager:
            # Show conversation summary
            try:
                context = conversation_manager.get_context(st.session_state.conversation_id, max_tokens=1000)
                if context and hasattr(context, 'summary') and context.summary:
                    with st.expander("📝 Conversation Summary", expanded=False):
                        st.markdown(context.summary)
            except Exception:
                pass  # Graceful degradation
        
        # Display recent messages
        recent_messages = st.session_state.messages[-8:] if len(st.session_state.messages) > 8 else st.session_state.messages
        
        for i, message in enumerate(recent_messages):
            with st.expander(f"{'👤' if message['role'] == 'user' else '🤖'} {message['role'].title()}", expanded=False):
                content_preview = message["content"][:150] + "..." if len(message["content"]) > 150 else message["content"]
                st.markdown(content_preview)
                
                if "timestamp" in message:
                    st.caption(f"⏰ {message['timestamp'][:19]}")
                
                # Enhanced message info
                if message["role"] == "assistant" and st.session_state.use_enhanced_mode:
                    if "confidence" in message:
                        st.caption(f"🎯 Confidence: {message['confidence']:.2f}")
                    if "citations" in message and message["citations"]:
                        st.caption(f"📚 Sources: {len(message['citations'])}")
        
        # Enhanced statistics
        if st.session_state.messages:
            st.markdown("### 📊 Session Statistics")
            user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
            assistant_messages = len([m for m in st.session_state.messages if m["role"] == "assistant"])
            
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("Questions", user_messages)
            with col_stat2:
                st.metric("Responses", assistant_messages)
            
            # Enhanced mode statistics
            if st.session_state.use_enhanced_mode:
                avg_confidence = 0
                total_sources = 0
                
                for msg in st.session_state.messages:
                    if msg["role"] == "assistant":
                        if "confidence" in msg:
                            avg_confidence += msg.get("confidence", 0)
                        if "citations" in msg:
                            total_sources += len(msg.get("citations", []))
                
                if assistant_messages > 0:
                    avg_confidence /= assistant_messages
                    st.metric("Avg Confidence", f"{avg_confidence:.2f}")
                    st.metric("Total Sources", total_sources)
            
            # Show active filters summary
            if active_filters:
                st.markdown("### 🔍 Active Filters")
                for filter_type, values in active_filters.items():
                    if isinstance(values, list):
                        st.caption(f"**{filter_type}:** {', '.join(values)}")
                    else:
                        st.caption(f"**{filter_type}:** {values}")

    # Enhanced chat history display
    st.markdown("---")
    if st.session_state.use_enhanced_mode:
        st.markdown("### 💬 Enhanced Conversation View")
    else:
        st.markdown("### 💬 Conversation History")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                ui_manager.render_enhanced_response(message["content"])
                
                # Show enhanced information in enhanced mode
                if st.session_state.use_enhanced_mode:
                    col_info1, col_info2, col_info3 = st.columns(3)
                    
                    with col_info1:
                        if "confidence" in message:
                            confidence = message["confidence"]
                            confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
                            st.caption(f"{confidence_color} Confidence: {confidence:.2f}")
                    
                    with col_info2:
                        if "citations" in message and message["citations"]:
                            st.caption(f"📚 {len(message['citations'])} sources")
                    
                    with col_info3:
                        if "timestamp" in message:
                            st.caption(f"⏰ {message['timestamp'][11:19]}")
            else:
                st.markdown(message["content"])
                
                # Show enhanced query info
                if st.session_state.use_enhanced_mode and "enhanced_query" in message and message["enhanced_query"]:
                    st.caption(f"🔍 Enhanced: {message['enhanced_query']}")
                
                if "filters" in message and message["filters"]:
                    filter_summary = ", ".join(message["filters"].keys())
                    st.caption(f"🎛️ Filters: {filter_summary}")

    # System information footer
    if st.session_state.use_enhanced_mode:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 🔧 System Info")
            
            try:
                health_status = system_components["health_monitor"].get_health_summary()
                
                # System metrics
                if "system_metrics" in health_status:
                    metrics = health_status["system_metrics"]
                    if "memory_usage_percent" in metrics:
                        st.caption(f"💾 Memory: {metrics['memory_usage_percent']:.1f}%")
                    if "response_time_avg" in metrics:
                        st.caption(f"⚡ Avg Response: {metrics['response_time_avg']:.2f}s")
                
                # Feature status
                enhanced_config = get_enhanced_config()
                active_features = sum(1 for feature, enabled in enhanced_config.get_all_features().items() 
                                    if feature.startswith('enable_') and enabled)
                st.caption(f"✨ Active Features: {active_features}")
                
            except Exception:
                st.caption("ℹ️ Enhanced mode active")

if __name__ == "__main__":
    main()