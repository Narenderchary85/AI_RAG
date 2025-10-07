import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .vectorstore import get_chroma_collection
from .config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, COLLECTION_NAME

os.makedirs(DATA_DIR, exist_ok=True)

def load_file(file_path):
    ext = file_path.lower().split(".")[-1]
    if ext == "pdf":
        loader = PyPDFLoader(file_path)
    elif ext in ("txt", "md"):
        loader = TextLoader(file_path, encoding="utf8")
    elif ext in ("docx", "doc"):
        loader = UnstructuredWordDocumentLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader.load()

def split_documents(docs, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(docs)

def persist_chunks_to_chroma(chunks, collection_name=COLLECTION_NAME):
    vectordb = get_chroma_collection(collection_name)
    vectordb.add_documents(chunks)
    vectordb.persist()
    return vectordb

def ingest_file(file_path, collection_name=COLLECTION_NAME):
    docs = load_file(file_path)
    chunks = split_documents(docs)
    persist_chunks_to_chroma(chunks, collection_name=collection_name)
    return {"ingested_chunks": len(chunks), "collection": collection_name}
