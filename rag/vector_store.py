from langchain_chroma import Chroma
from config.llm_config import get_embeddings
import chromadb
from chromadb.config import Settings

DB_DIR = "./vector_db"
COLLECTION_NAME = "knowledge_base"  # must be 3-512 chars and valid pattern

def _client():
    return chromadb.Client(
        Settings(
            persist_directory=DB_DIR,
            anonymized_telemetry=False,
        )
    )

def create_db(chunks: list[str]):
    embeddings = get_embeddings()
    client = _client()
    db = Chroma.from_texts(
        texts=chunks,
        embedding=embeddings,
        client=client,
        collection_name=COLLECTION_NAME,
    )
    return db

def load_db():
    embeddings = get_embeddings()
    client = _client()
    return Chroma(
        client=client,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )