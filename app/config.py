import os
from dotenv import load_dotenv

load_dotenv()

PPLX_API_KEY = os.getenv("PPLX_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY") 
CHROMA_PERSIST_DIR = os.getenv("CHROMA_DIR", "chroma_db")
DATA_DIR = os.getenv("DATA_DIR", "data")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "default_collection")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
LLM_MODEL = os.getenv("LLM_MODEL", "sonar-pro")


