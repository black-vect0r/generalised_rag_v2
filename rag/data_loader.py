import csv
from pdfminer.high_level import extract_text
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_guidelines_chunks(path: str) -> list[str]:
    text = extract_text(path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_text(text)

def load_problem_chunks(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    return splitter.split_text(text)

def csv_schema_and_sample_text(csv_path: str, sample_rows: int = 25) -> list[str]:
    """
    IMPORTANT: Do NOT embed all 50,000 rows.
    We embed only schema + small sample for RAG grounding.
    """
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        rows = []
        for i, r in enumerate(reader):
            if i >= sample_rows:
                break
            rows.append(r)

    schema = "CSV Schema:\n" + "\n".join([f"- {col}" for col in header]) if header else "CSV Schema: (no header detected)"

    sample_lines = []
    if header and rows:
        sample_lines.append("CSV Sample Rows:")
        for r in rows:
            pairs = [f"{header[j]}={r[j] if j < len(r) else ''}" for j in range(len(header))]
            sample_lines.append(", ".join(pairs))

    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=100)
    chunks = splitter.split_text(schema + "\n\n" + "\n".join(sample_lines))
    return chunks