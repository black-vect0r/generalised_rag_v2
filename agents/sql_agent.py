import hashlib
import re
from datetime import datetime
from typing import List, Tuple

from config.llm_config import get_llm
from rag.retriever import get_retriever
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
    if "--" in s or "/*" in s:
        return False
    for b in _BLOCKED_SQL:
        if re.search(rf"\b{b}\b", s):
            return False
    for fn in _BLOCKED_FUNCS:
        if re.search(rf"\b{fn}\b", s):
            return False
    return True


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
        return f'SELECT * FROM "{table_name}" ORDER BY CAST("{col}" AS REAL) DESC LIMIT 30'
    return f'SELECT * FROM "{table_name}" LIMIT 30'


def _is_admin_or_unsafe_intent(user_query: str) -> bool:
    q = user_query.lower()
    admin_terms = [
        "pragma", "vacuum", "drop", "delete", "update", "insert", "alter",
        "create table", "attach", "detach", "reindex", "truncate"
    ]
    return any(t in q for t in admin_terms)


def _to_float(value) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _mask_id(raw: str) -> str:
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:6]
    return f"ID_{digest}"


def _mask_date(raw: str) -> str:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            return dt.strftime("%Y-%m")
        except Exception:
            continue
    return raw[:7] if len(raw) >= 7 else "date"


def _transform_value(col: str, value) -> str:
    s = "" if value is None else str(value).strip()
    if not s:
        return "n/a"

    cl = col.lower()
    if any(k in cl for k in ["client", "trader", "name", "account", "id", "order", "trade"]):
        return _mask_id(s)

    if any(k in cl for k in ["date", "time", "timestamp"]):
        return _mask_date(s)

    n = _to_float(s)
    if n is not None:
        if abs(n) >= 1_000_000:
            return f"~{round(n / 1_000_000, 2)}M"
        if abs(n) >= 1_000:
            return f"~{round(n / 1_000, 2)}K"
        return f"~{round(n, 2)}"

    if len(s) > 14:
        return s[:10] + "..."
    return s


def _transformed_preview(cols: List[str], rows: List[tuple], limit: int = 12) -> str:
    if not cols or not rows:
        return "No rows available."

    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = []
    for row in rows[:limit]:
        values = [_transform_value(c, v) for c, v in zip(cols, row)]
        body.append("| " + " | ".join(values) + " |")

    return "\n".join([header, sep, *body])


def answer_with_sql(query: str, db_path: str, table_name: str = "trades", history: str = "") -> str:
    if _is_admin_or_unsafe_intent(query):
        return (
            "This request looks like a database admin or modifying operation, which is blocked. "
            "Please ask a read-only analytics question (for example, top trends, grouped counts, or range analysis)."
        )

    try:
        retriever = get_retriever()
        policy_docs = retriever.invoke(query)
        policy_context = "\n".join([d.page_content for d in policy_docs]).strip()
    except Exception:
        policy_context = ""

    schema = get_sqlite_schema(db_path, table_name)
    cols_in_table = _extract_columns_from_schema(schema)

    sql_prompt = f"""
You are an expert SQLite analyst. Generate a SAFE query.

Conversation history:
{history if history else "(none)"}

Rules:
- Output one query only.
- Only SELECT or WITH...SELECT.
- Include LIMIT 30.
- Use only listed columns.
- No modifying/admin commands.
- Cast numeric text columns as REAL for numeric operations.

Schema:
{schema}

User question:
{query}
"""

    try:
        sql = llm.invoke(sql_prompt).content.strip().strip("`").strip()
    except Exception:
        sql = _fallback_sql(table_name, cols_in_table)

    if "limit" not in sql.lower():
        sql = sql.rstrip().rstrip(";") + " LIMIT 30"

    if not _is_safe_sql(sql):
        sql = _fallback_sql(table_name, cols_in_table)

    try:
        cols, rows = run_sql_query(db_path, sql)
    except Exception:
        sql = _fallback_sql(table_name, cols_in_table)
        cols, rows = run_sql_query(db_path, sql)

    if not rows:
        return "I could not find matching data for that request. Try narrowing by symbol, venue, or date range."

    transformed_table = _transformed_preview(cols, rows)

    interpret_prompt = f"""
You are a policy-aware chatbot in a public demo.

Conversation history:
{history if history else "(none)"}

Policy context:
{policy_context if policy_context else "No policy context available."}

User question:
{query}

Transformed data preview (already anonymized and approximate):
{transformed_table}

Response rules:
- Give a natural, concise answer.
- Mention key trends and notable comparisons.
- Keep response to at most 4 short sentences or 4 bullets.
- Do not reveal exact raw records, exact identifiers, SQL text, or backend internals.
- If needed, suggest one follow-up filter to improve precision.
"""

    try:
        answer = llm.invoke(interpret_prompt).content.strip()
    except Exception:
        answer = "I analyzed an anonymized slice of the data but could not finalize the narrative. Please retry."

    return answer
