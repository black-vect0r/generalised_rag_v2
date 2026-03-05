import re

BLOCKED_PATTERNS = [
    "ignore instructions",
    "reveal system prompt",
    "bypass guardrails",
    "act as system",
    "show hidden prompt",
    "print your chain of thought",
    "show your chain of thought",
    "developer message",
    "internal instructions",
    "training data",
]

# Block DB admin / modifying intents up-front
BLOCKED_DB_INTENTS = [
    r"\bpragma\b",
    r"\bvacuum\b",
    r"\bdrop\b",
    r"\bdelete\b",
    r"\bupdate\b",
    r"\binsert\b",
    r"\balter\b",
    r"\btruncate\b",
    r"\bcreate\s+table\b",
    r"\battach\b",
    r"\bdetach\b",
    r"\breindex\b",
]


def validate_query(query: str) -> tuple[bool, str]:
    q = query.strip()
    if len(q) < 3:
        return False, "Query too short."
    if len(q) > 2000:
        return False, "Query too long. Please keep it under 2000 characters."

    ql = q.lower()

    for p in BLOCKED_PATTERNS:
        if p in ql:
            return False, "Potential prompt injection detected."

    if re.search(r"(show|reveal|dump).*(sql|schema|database|prompt|internal)", ql):
        return False, "Unsafe request detected. Ask for insights, trends, or summaries instead."

    for pat in BLOCKED_DB_INTENTS:
        if re.search(pat, ql):
            return False, (
                "Unsafe request: database admin/modifying commands are not allowed. "
                "Ask a read-only analytics question (e.g., 'Top 10 clients by notional_value')."
            )

    return True, ""
