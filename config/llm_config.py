import os

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("GENAI_BASE_URL", "https://genailab.tcs.in")
LLM_MODEL = os.getenv("GENAI_LLM_MODEL", "azure_ai/genailab-maas-DeepSeek-V3-0324")
EMBED_MODEL = os.getenv("GENAI_EMBED_MODEL", "azure/genailab-maas-text-embedding-3-large")
API_KEY = os.getenv("GENAI_API_KEY", "").strip()

client = httpx.Client(verify=False, timeout=60.0)


def _require_api_key() -> str:
    if API_KEY:
        return API_KEY
    fallback = os.getenv("OPENAI_API_KEY", "").strip()
    if fallback:
        return fallback
    # Non-empty placeholder keeps app startup non-blocking; request-time errors are handled in agents.
    return "missing-api-key"


def get_llm():
    return ChatOpenAI(
        base_url=BASE_URL,
        model=LLM_MODEL,
        api_key=_require_api_key(),
        http_client=client,
        temperature=0.1,
    )


def get_embeddings():
    return OpenAIEmbeddings(
        base_url=BASE_URL,
        model=EMBED_MODEL,
        api_key=_require_api_key(),
        http_client=client,
    )
