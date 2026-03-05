import re

BLOCKED_PATTERNS = [
    "ignore instructions",
    "reveal system prompt",
    "bypass guardrails",
    "act as system",
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
        return False, "⚠️ Query too short."

    ql = q.lower()

    for p in BLOCKED_PATTERNS:
        if p in ql:
            return False, "⚠️ Potential prompt injection detected."

    for pat in BLOCKED_DB_INTENTS:
        if re.search(pat, ql):
            return False, (
                "🚫 Unsafe request: database admin/modifying commands are not allowed. "
                "Ask a read-only analytics question (e.g., 'Top 10 clients by notional_value')."
            )

    return True, ""