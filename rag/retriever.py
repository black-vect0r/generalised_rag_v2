from rag.vector_store import load_db

def get_retriever():
    db = load_db()
    return db.as_retriever(search_kwargs={"k": 5})