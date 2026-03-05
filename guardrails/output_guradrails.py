SENSITIVE_TERMS = [
    "password",
    "secret",
    "api key",
    "private key"
]


def validate_output(response):

    text = response["result"]

    for term in SENSITIVE_TERMS:
        if term in text.lower():
            return "⚠️ Sensitive content detected. Response blocked."

    return text