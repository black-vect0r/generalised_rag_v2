import re

SENSITIVE_TERMS = [
    "api key",
    "password",
    "secret",
    "private key",
    "system prompt",
    "developer message",
    "internal instruction",
    "chain of thought",
]

LEAK_PATTERNS = [
    r"```sql",
    r"\bselect\b.+\bfrom\b",
    r"\bpragma\b",
    r"\bdrop\b",
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"traceback",
    r"exception",
]


def _clean_text(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"\|\s*---[\s\S]*", "", text)  # strip markdown tables
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _limit_bullets(text: str, max_bullets: int = 4) -> str:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    bullets = [ln for ln in lines if re.match(r"^[-*\d]+[.)]?\s+", ln)]
    if not bullets:
        return text

    kept = []
    count = 0
    for ln in lines:
        if re.match(r"^[-*\d]+[.)]?\s+", ln):
            count += 1
            if count <= max_bullets:
                kept.append(ln)
        else:
            kept.append(ln)
    return "\n".join(kept).strip()


def _limit_sentences(text: str, max_sentences: int = 4, max_chars: int = 560) -> str:
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0].strip() + "..."

    parts = re.split(r"(?<=[.!?])\s+", text)
    if len(parts) > max_sentences:
        text = " ".join(parts[:max_sentences]).strip()
    return text


def filter_output(text: str) -> str:
    normalized = text.lower()

    for term in SENSITIVE_TERMS:
        if term in normalized:
            return "I can share the result, but sensitive or internal details are hidden."

    for pat in LEAK_PATTERNS:
        if re.search(pat, normalized, flags=re.DOTALL):
            return "I can provide a safe summary, but internal query details are hidden by policy."

    cleaned = _clean_text(text)
    cleaned = _limit_bullets(cleaned, max_bullets=4)
    cleaned = _limit_sentences(cleaned, max_sentences=4, max_chars=560)
    return cleaned if cleaned else "I could not produce a safe concise response. Please try again."
