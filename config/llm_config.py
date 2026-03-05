from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import httpx

BASE_URL = "https://genailab.tcs.in"
API_KEY = "sk-CRBo0MaN4rJGCIjIBZ5y5Q"

client = httpx.Client(verify=False)

def get_llm():
    return ChatOpenAI(
        base_url=BASE_URL,
        model="azure_ai/genailab-maas-DeepSeek-V3-0324",
        api_key=API_KEY,
        http_client=client,
        temperature=0,
    )

def get_embeddings():
    return OpenAIEmbeddings(
        base_url=BASE_URL,
        model="azure/genailab-maas-text-embedding-3-large",
        api_key=API_KEY,
        http_client=client,
    )