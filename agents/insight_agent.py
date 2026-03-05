from rag.retriever import get_retriever
from config.llm_config import get_llm

llm = get_llm()

def generate_insights() -> str:
    retriever = get_retriever()
    docs = retriever.invoke("key risks, compliance concerns, recommended actions")
    context = "\n".join([d.page_content for d in docs])

    prompt = f"""
Generate:
1) Key Insights
2) Risks / Compliance Issues
3) Recommended Actions

Use only the context.

Context:
{context}
"""
    return llm.invoke(prompt).content.strip()