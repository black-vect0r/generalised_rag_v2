from config.llm_config import get_llm

llm = get_llm()

def evaluate_answer(question: str, answer: str, context: str) -> str:
    prompt = f"""
You are an AI evaluator.

Evaluate whether the answer is supported by the context.

Question:
{question}

Answer:
{answer}

Context:
{context}

Return exactly:
Confidence Score: <0-100>
Hallucination Risk: <Low/Medium/High>
Explanation: <1-3 sentences>
"""
    return llm.invoke(prompt).content.strip()