import csv
import os
import sqlite3
from typing import List, Tuple

def _sanitize_col(name: str) -> str:
    name = name.strip().replace("\n", " ").replace("\t", " ")
    name = "".join(ch if ch.isalnum() or ch in ("_", " ") else "_" for ch in name)
    name = name.strip().replace(" ", "_")
    if not name:
        name = "col"
    if name[0].isdigit():
        name = "c_" + name
    return name[:60]

def _guess_index_cols(cols: List[str]) -> List[str]:
    """
    Heuristic indexes for speed (optional but helps demos).
    """
    candidates = []
    lowered = [c.lower() for c in cols]
    for key in ["date", "time", "symbol", "scrip", "isin", "client", "trader", "member", "id", "order", "trade"]:
        for i, c in enumerate(lowered):
            if key in c and cols[i] not in candidates:
                candidates.append(cols[i])
    return candidates[:3]  # keep it small

def load_csv_to_sqlite(csv_path: str, db_path: str, table_name: str = "trades") -> Tuple[str, List[str]]:
    """
    Loads CSV into SQLite. Uses TEXT columns for speed & simplicity.
    For hackathons: reliable, fast, avoids dtype inference issues.
    Returns (table_name, columns).
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=-200000;")  # ~200MB cache if available

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        raw_header = next(reader, [])
        cols = [_sanitize_col(c) for c in raw_header] if raw_header else []

        if not cols:
            raise ValueError("CSV header not found. Please ensure the first row contains column names.")

        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        col_defs = ", ".join([f'"{c}" TEXT' for c in cols])
        conn.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

        columns_sql = ", ".join([f'"{c}"' for c in cols])
        placeholders = ", ".join(["?"] * len(cols))

        insert_sql = f'INSERT INTO "{table_name}" ({columns_sql}) VALUES ({placeholders})'
        batch = []
        batch_size = 2000

        conn.execute("BEGIN")
        for row in reader:
            if len(row) < len(cols):
                row = row + [""] * (len(cols) - len(row))
            elif len(row) > len(cols):
                row = row[: len(cols)]
            batch.append(row)

            if len(batch) >= batch_size:
                conn.executemany(insert_sql, batch)
                batch.clear()

        if batch:
            conn.executemany(insert_sql, batch)

        conn.execute("COMMIT")

        # Optional indexes
        for ic in _guess_index_cols(cols):
            try:
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_{ic} ON "{table_name}"("{ic}")')
            except Exception:
                pass

    conn.close()
    return table_name, cols

def get_sqlite_schema(db_path: str, table_name: str = "trades") -> str:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    conn.close()

    if not rows:
        return f"Table '{table_name}' not found."

    # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
    cols = [r[1] for r in rows]
    return "Table: " + table_name + "\nColumns:\n" + "\n".join([f"- {c}" for c in cols])

def run_sql_query(db_path: str, sql: str) -> Tuple[List[str], List[tuple]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchmany(50)  # hard limit for UI
    conn.close()
    return cols, rows