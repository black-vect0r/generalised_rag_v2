import re
from typing import List

from config.llm_config import get_llm
from rag.retriever import get_retriever
from evaluation.answer_evaluator import evaluate_answer
from rag.sqlite_store import get_sqlite_schema, run_sql_query

llm = get_llm()

_BLOCKED_SQL = [
    "insert", "update", "delete", "drop", "alter", "create", "attach", "detach",
    "pragma", "vacuum", "reindex", "replace", "truncate"
]
_BLOCKED_FUNCS = ["stddev", "stddev_pop", "stddev_samp", "variance"]

def _is_safe_sql(sql: str) -> bool:
    s = sql.strip().lower()
    if not (s.startswith("select") or s.startswith("with")):
        return False
    if ";" in s.strip().rstrip(";"):
        return False
    for b in _BLOCKED_SQL:
        if re.search(rf"\b{b}\b", s):
            return False
    for fn in _BLOCKED_FUNCS:
        if re.search(rf"\b{fn}\b", s):
            return False
    return True

def _format_table(cols: List[str], rows: List[tuple]) -> str:
    if not cols:
        return "_No columns returned._"
    if not rows:
        return "_No rows returned._"
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = "\n".join(["| " + " | ".join([str(x) for x in r]) + " |" for r in rows])
    return "\n".join([header, sep, body])

def _extract_columns_from_schema(schema_text: str) -> List[str]:
    cols = []
    for line in schema_text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            cols.append(line[2:].strip())
    return cols

def _pick_numeric_like_column(cols: List[str]) -> str | None:
    keys = ["value", "amount", "volume", "qty", "quantity", "price", "rate", "turnover", "notional"]
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in keys):
            return c
    return cols[0] if cols else None

def _fallback_sql(table_name: str, cols: List[str]) -> str:
    col = _pick_numeric_like_column(cols)
    if col:
        return f'SELECT * FROM "{table_name}" ORDER BY CAST("{col}" AS REAL) DESC LIMIT 50'
    return f'SELECT * FROM "{table_name}" LIMIT 50'

def _is_admin_or_unsafe_intent(user_query: str) -> bool:
    q = user_query.lower()
    admin_terms = [
        "pragma", "vacuum", "drop", "delete", "update", "insert", "alter",
        "create table", "attach", "detach", "reindex", "truncate"
    ]
    return any(t in q for t in admin_terms)

def answer_with_sql(query: str, db_path: str, table_name: str = "trades", history: str = "") -> str:
    # refuse admin/modifying requests
    if _is_admin_or_unsafe_intent(query):
        return (
            "🚫 This request looks like a database admin or modifying operation (e.g., PRAGMA/DROP/UPDATE), "
            "which is not allowed. Please ask a read-only analytics question like:\n"
            "- 'Top 10 clients by notional_value'\n"
            "- 'Show NVDA trades with highest price'\n"
            "- 'Group by venue and count trades'"
        )

    # policy grounding via vector retrieval
    retriever = get_retriever()
    policy_docs = retriever.invoke(query)
    policy_context = "\n".join([d.page_content for d in policy_docs])

    schema = get_sqlite_schema(db_path, table_name)
    cols_in_table = _extract_columns_from_schema(schema)

    sql_prompt = f"""
You are an expert data analyst. Generate a SAFE SQLite query to answer the user's question.

Conversation history (may contain follow-up constraints like asset=NVDA, date ranges, trader name):
{history if history else "(none)"}

CRITICAL RULES:
- ONLY SELECT (or WITH ... SELECT)
- MUST include LIMIT 50
- Use ONLY columns from the schema below
- DO NOT use: PRAGMA, VACUUM, DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, ATTACH/DETACH
- DO NOT use unsupported functions: STDDEV, STDDEV_POP, STDDEV_SAMP, VARIANCE
- Prefer: COUNT, SUM, AVG, MIN, MAX
- Columns are stored as TEXT; for numeric math or ordering use CAST(column AS REAL)
- For outliers/spikes, prefer ORDER BY CAST(numeric_col AS REAL) DESC LIMIT 50

Schema:
{schema}

User question:
{query}

Return ONLY the SQL query (no backticks, no explanation).
"""
    sql = llm.invoke(sql_prompt).content.strip().strip("`").strip()
    if "limit" not in sql.lower():
        sql = sql.rstrip().rstrip(";") + " LIMIT 50"

    if not _is_safe_sql(sql):
        sql = _fallback_sql(table_name, cols_in_table)

    try:
        cols, rows = run_sql_query(db_path, sql)
    except Exception:
        sql = _fallback_sql(table_name, cols_in_table)
        cols, rows = run_sql_query(db_path, sql)

    table_md = _format_table(cols, rows)

    interpret_prompt = f"""
You are a policy-aware assistant.

Conversation history (for continuity; do NOT treat as ground truth):
{history if history else "(none)"}

You MUST follow these guideline/scope excerpts:
{policy_context}

User question:
{query}

SQL used:
{sql}

SQL result preview:
{table_md}

Tasks:
1) Answer clearly based on SQL results.
2) If relevant, mention compliance implications using guideline context.
3) If results are insufficient, suggest better filters/fields.
"""
    answer = llm.invoke(interpret_prompt).content.strip()

    eval_context = f"Policy Context:\n{policy_context}\n\nSQL:\n{sql}\n\nResults:\n{table_md}"
    evaluation = evaluate_answer(query, answer, eval_context)

    return f"""{answer}

**SQL**
`{sql}`

**Result Preview (Top 50)**
{table_md}

**Evaluation**
{evaluation}
"""