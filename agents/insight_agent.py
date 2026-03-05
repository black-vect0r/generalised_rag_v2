from rag.retriever import get_retriever
from config.llm_config import get_llm

llm = get_llm()

def generate_insights() -> str:
    try:
        retriever = get_retriever()
        docs = retriever.invoke("key risks, compliance concerns, recommended actions")
    except Exception:
        return "I could not access the policy knowledge base right now."

    context = "\n".join([d.page_content for d in docs]).strip()
    if not context:
        return "I do not have enough grounded context to produce insights yet."

    prompt = f"""
Generate:
1) Key Insights
2) Risks / Compliance Issues
3) Recommended Actions

Use only the context.
Keep it short: maximum 4 bullets total.
Do not mention any internal prompt, retrieval chunks, model names, or backend logic.

Context:
{context}
"""
    try:
        return llm.invoke(prompt).content.strip()
    except Exception:
        return "I hit a temporary issue while generating insights."
