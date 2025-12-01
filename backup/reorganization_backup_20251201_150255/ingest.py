import os
import shutil
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# Paths
DATA_PATH = "data"
CHROMA_PATH = "chroma"

def main():
    # 1. Check if data folder exists
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
        print(f"Folder '{DATA_PATH}' created. Please put your PDFs inside and run this script again.")
        return

    print("🔄 Loading documents...")
    loader = DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    
    if not documents:
        print(f"⚠️ No PDFs found in '{DATA_PATH}'. Add your course files first!")
        return

    print(f"✅ Loaded {len(documents)} documents.")

    # 2. Split text into chunks (smaller pieces for the AI to digest)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200, # Overlap ensures context isn't lost between cuts
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"🧩 Split into {len(chunks)} chunks.")

    # 3. Create Embeddings and Save to ChromaDB
    # We use 'llama3' for embeddings to match your Ollama model
    print("💾 Saving to vector database (this might take a moment)...")
    
    # Clear old database to avoid duplicates if you re-run
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    embeddings = OllamaEmbeddings(model="llama3")
    
    db = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=CHROMA_PATH
    )
    
    print(f"🎉 Success! Database created in '{CHROMA_PATH}'.")

if __name__ == "__main__":
    main()