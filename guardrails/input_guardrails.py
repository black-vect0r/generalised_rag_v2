BLOCKED_PATTERNS = [
    "ignore previous instructions",
    "reveal system prompt",
    "bypass guardrails",
    "act as system"
]


def validate_input(query):

    q = query.lower()

    for pattern in BLOCKED_PATTERNS:
        if pattern in q:
            return False, "⚠️ Prompt injection detected."

    if len(query) < 3:
        return False, "⚠️ Query too short."

    return True, ""