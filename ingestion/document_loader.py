from pdfminer.high_level import extract_text
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_document(file_path):

    text = extract_text(file_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_text(text)

    return chunks