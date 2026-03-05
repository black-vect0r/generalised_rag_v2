from config.llm_config import get_llm

llm = get_llm()

def route_query(query: str, history: str = "") -> str:
    prompt = f"""
Classify the user query into ONE category:

QA        (policy/guidelines reasoning or general questions grounded in PDF/TXT)
SUMMARY   (summarize guidelines/problem)
INSIGHT   (risks + recommendations grounded in PDF/TXT)
DATA      (requires analyzing the synthetic CSV data using SQLite)

Conversation history (may help interpret follow-ups):
{history if history else "(none)"}

Query: {query}

Return ONLY: QA or SUMMARY or INSIGHT or DATA
"""
    response = llm.invoke(prompt)
    route = response.content.strip().upper()

    if "DATA" in route:
        return "DATA"
    if "SUMMARY" in route:
        return "SUMMARY"
    if "INSIGHT" in route:
        return "INSIGHT"
    return "QA"