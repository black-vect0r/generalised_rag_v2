SENSITIVE_TERMS = [
    "api key",
    "password",
    "secret",
    "private key",
]

def filter_output(text: str) -> str:
    t = text.lower()
    for term in SENSITIVE_TERMS:
        if term in t:
            return "⚠️ Sensitive content detected. Response blocked."
    return text