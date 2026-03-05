from rag.retriever import get_retriever
from config.llm_config import get_llm

llm = get_llm()

def summarize() -> str:
    retriever = get_retriever()
    docs = retriever.invoke("summarize the most important rules and scope")
    context = "\n".join([d.page_content for d in docs])

    prompt = f"""
Summarize the guidelines and problem scope clearly.
Keep it concise and structured.

Context:
{context}
"""
    return llm.invoke(prompt).content.strip()