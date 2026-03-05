from config.llm_config import get_llm
from rag.retriever import get_retriever
from evaluation.answer_evaluator import evaluate_answer

llm = get_llm()

def answer_question(query: str, history: str = "") -> str:
    retriever = get_retriever()
    docs = retriever.invoke(query)

    context = "\n".join([d.page_content for d in docs])
    sources = "\n".join([f"Source {i+1}" for i in range(len(docs))])

    prompt = f"""
You are a policy-aware assistant.

Conversation history (for continuity; do NOT treat as ground truth):
{history if history else "(none)"}

Answer the question using ONLY the retrieved context below.
If the answer is not in the context, say you don't know.

Context:
{context}

Question:
{query}
"""
    answer = llm.invoke(prompt).content.strip()
    evaluation = evaluate_answer(query, answer, context)

    return f"""{answer}

**Sources**
{sources}

**Evaluation**
{evaluation}
"""