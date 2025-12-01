import streamlit as st
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

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
    st.set_page_config(page_title="Assistant Smart ICT", page_icon="🎓")
    
    st.title("🎓 Assistant Virtuel - Smart ICT")
    st.subheader("INPT - Institut National des Postes et Télécommunications")
    
    # Check if database exists
    try:
        db = get_vectorstore()
    except Exception:
        st.error("Erreur : La base de données est introuvable. Avez-vous lancé 'ingest.py' ?")
        return

    # Initialize Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle User Input
    if prompt := st.chat_input("Posez votre question sur les modules (ex: Syllabus Réseaux)..."):
        
        # 1. Display User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Generate Answer
        with st.chat_message("assistant"):
            with st.spinner("Recherche dans les cours..."):
                try:
                    # Setup LLM and Retriever
                    llm = ChatOllama(model=OLLAMA_MODEL)
                    retriever = db.as_retriever(search_kwargs={"k": 5}) # Retrieve top 5 relevant chunks
                    
                    # Create Chains
                    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
                    question_answer_chain = create_stuff_documents_chain(llm, prompt_template)
                    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
                    
                    # Run Chain
                    response = rag_chain.invoke({"input": prompt})
                    answer = response["answer"]
                    
                    st.markdown(answer)
                    
                    # Save Assistant Message
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                except Exception as e:
                    st.error(f"Une erreur est survenue : {e}")
                    st.info("Assurez-vous que Ollama est lancé en arrière-plan.")

if __name__ == "__main__":
    main()