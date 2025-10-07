from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings  
from .config import CHROMA_PERSIST_DIR, COLLECTION_NAME

def get_chroma_collection(collection_name=COLLECTION_NAME):
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2",model_kwargs={"device": "cpu"})
    vectordb = Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        collection_name=collection_name,
        embedding_function=embeddings
    )
    return vectordb

def get_retriever(k=5, collection_name=COLLECTION_NAME):
    vectordb = get_chroma_collection(collection_name)
    return vectordb.as_retriever(search_kwargs={"k": k})
