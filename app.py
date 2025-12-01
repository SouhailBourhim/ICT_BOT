import streamlit as st
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import uuid
from datetime import datetime

# Import enhanced UI components
from ui.components import UIComponentManager
from ui.filters import SearchEnhancementManager

# Configuration
CHROMA_PATH = "chroma"
OLLAMA_MODEL = "llama3"

# Custom Prompt Template (French)
PROMPT_TEMPLATE = """
Tu es un assistant éducatif pour les étudiants en Smart ICT à l'INPT.
Réponds à la question suivante en te basant **uniquement** sur le contexte fourni ci-dessous.
Si la réponse ne se trouve pas dans le contexte, dis poliment que tu ne sais pas. N'invente pas d'informations.

<contexte>
{context}
</contexte>

Question de l'étudiant : {input}
"""

def get_vectorstore():
    """Loads the existing Chroma database."""
    embeddings = OllamaEmbeddings(model=OLLAMA_MODEL)
    # Load the persisted database
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    return db

def main():
    st.set_page_config(
        page_title="Assistant Smart ICT", 
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize UI components
    ui_manager = UIComponentManager()
    search_manager = SearchEnhancementManager()
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())
    
    # Main header
    st.title("🎓 Assistant Virtuel - Smart ICT")
    st.subheader("INPT - Institut National des Postes et Télécommunications")
    
    # Render filter sidebar
    active_filters = search_manager.render_filter_sidebar()
    
    # Check if database exists
    try:
        db = get_vectorstore()
    except Exception:
        st.error("Erreur : La base de données est introuvable. Avez-vous lancé 'ingest.py' ?")
        return

    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Enhanced input with auto-complete
        st.markdown("### 💬 Posez votre question")
        prompt = ui_manager.render_enhanced_input("main_query")
        
        # Search enhancements
        if prompt:
            search_manager.render_search_enhancements(prompt)
        
        # Chat interface
        if prompt:
            # Apply filters to query
            enhanced_query = search_manager.apply_filters_to_query(prompt, active_filters)
            
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
                    try:
                        # Setup LLM and Retriever
                        llm = ChatOllama(model=OLLAMA_MODEL)
                        
                        # Apply filters to retriever if available
                        search_kwargs = {"k": 5}
                        if enhanced_query.get("metadata_filters"):
                            search_kwargs["filter"] = enhanced_query["metadata_filters"]
                        
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
                        
                    except Exception as e:
                        st.error(f"Une erreur est survenue : {e}")
                        st.info("Assurez-vous que Ollama est lancé en arrière-plan.")
    
    with col2:
        # Chat history and conversation management
        st.markdown("### 📜 Historique de conversation")
        
        if st.button("🗑️ Nouvelle conversation", key="new_conversation"):
            st.session_state.messages = []
            st.session_state.conversation_id = str(uuid.uuid4())
            st.rerun()
        
        # Display recent messages (last 5)
        recent_messages = st.session_state.messages[-10:] if len(st.session_state.messages) > 10 else st.session_state.messages
        
        for i, message in enumerate(recent_messages):
            with st.expander(f"{'👤' if message['role'] == 'user' else '🤖'} {message['role'].title()}", expanded=False):
                st.markdown(message["content"][:200] + "..." if len(message["content"]) > 200 else message["content"])
                if "timestamp" in message:
                    st.caption(f"⏰ {message['timestamp'][:19]}")
        
        # Conversation statistics
        if st.session_state.messages:
            st.markdown("### 📊 Statistiques")
            user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
            assistant_messages = len([m for m in st.session_state.messages if m["role"] == "assistant"])
            
            st.metric("Questions posées", user_messages)
            st.metric("Réponses données", assistant_messages)
            
            # Show active filters summary
            if active_filters:
                st.markdown("### 🔍 Filtres actifs")
                for filter_type, values in active_filters.items():
                    if isinstance(values, list):
                        st.write(f"**{filter_type}:** {', '.join(values)}")
                    else:
                        st.write(f"**{filter_type}:** {values}")

    # Display full chat history
    st.markdown("---")
    st.markdown("### 💬 Conversation complète")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                ui_manager.render_enhanced_response(message["content"])
            else:
                st.markdown(message["content"])

if __name__ == "__main__":
    main()