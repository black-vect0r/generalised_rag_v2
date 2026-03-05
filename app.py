import hashlib
import os

import streamlit as st

from agents.insight_agent import generate_insights
from agents.qa_agent import answer_question
from agents.router_agent import route_query
from agents.sql_agent import answer_with_sql
from agents.summarizer_agent import summarize
from chat.session_store import (
    add_message,
    create_chat,
    delete_chat,
    get_active_messages,
    history_text,
    init_state,
    set_active_chat,
)
from guardrails.input_guard import validate_query
from guardrails.output_guard import filter_output
from rag.data_loader import (
    csv_schema_and_sample_text,
    load_guidelines_chunks,
    load_problem_chunks,
)
from rag.sqlite_store import load_csv_to_sqlite
from rag.vector_store import create_db

st.set_page_config(page_title="Sentinel RAG Assistant", layout="wide")

st.markdown(
    """
<style>
:root {
    --bg: #f6f4ef;
    --card: #ffffff;
    --ink: #1f2937;
    --muted: #6b7280;
    --brand: #0f766e;
    --brand-soft: #ccfbf1;
    --accent: #b45309;
}

.stApp {
    background:
        radial-gradient(circle at 10% 10%, #e6fffa 0%, rgba(230,255,250,0) 32%),
        radial-gradient(circle at 95% 5%, #fff7ed 0%, rgba(255,247,237,0) 30%),
        var(--bg);
}

.main .block-container {
    padding-top: 1.2rem;
    max-width: 1050px;
}

.hero {
    background: linear-gradient(120deg, #0f766e 0%, #115e59 50%, #134e4a 100%);
    color: #f8fafc;
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 14px;
    border: 1px solid rgba(255,255,255,0.18);
}

.hero h1 {
    margin: 0;
    font-size: 1.45rem;
    letter-spacing: 0.2px;
}

.hero p {
    margin: 6px 0 0;
    color: #d1fae5;
    font-size: 0.93rem;
}

.quickbar {
    margin: 0.25rem 0 0.8rem;
}

div[data-testid="stChatMessage"] {
    border-radius: 14px;
    border: 1px solid #e5e7eb;
    background: var(--card);
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

div[data-testid="stChatMessage"] p {
    color: var(--ink);
}

.sidebar-card {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 12px;
    padding: 10px;
    margin-top: 12px;
}

.small-note {
    color: var(--muted);
    font-size: 0.82rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
  <h1>Sentinel RAG Assistant</h1>
  <p>Policy-grounded AI agent with privacy-safe, transformed data responses for live demos.</p>
</div>
""",
    unsafe_allow_html=True,
)

GUIDE_PATH = "data/guidelines.pdf"
PROB_PATH = "data/problem_statement.txt"
CSV_PATH = "data/synthetic_data.csv"

SQLITE_DB_PATH = "data/synthetic_data.db"
SQLITE_TABLE = "trades"

INDEX_MARKER = "vector_db/.index_fingerprint"
SQL_MARKER = "data/.sql_fingerprint"


def _fingerprint(paths: list[str]) -> str:
    h = hashlib.sha256()
    for p in paths:
        stat = os.stat(p)
        h.update(p.encode("utf-8"))
        h.update(str(stat.st_mtime_ns).encode("utf-8"))
        h.update(str(stat.st_size).encode("utf-8"))
    return h.hexdigest()


def _safe_fingerprint(paths: list[str]) -> str | None:
    try:
        return _fingerprint(paths)
    except FileNotFoundError as err:
        st.error(f"Missing required file: {err.filename}")
    except Exception as err:
        st.error(f"Failed to inspect project files: {err}")
    return None


def _healthcheck() -> list[tuple[str, bool, str]]:
    checks = []
    checks.append(("API key", bool(os.getenv("GENAI_API_KEY") or os.getenv("OPENAI_API_KEY")), "Set GENAI_API_KEY in .env"))
    checks.append(("Guidelines file", os.path.exists(GUIDE_PATH), GUIDE_PATH))
    checks.append(("Problem statement", os.path.exists(PROB_PATH), PROB_PATH))
    checks.append(("CSV dataset", os.path.exists(CSV_PATH), CSV_PATH))
    checks.append(("Vector index marker", os.path.exists(INDEX_MARKER), INDEX_MARKER))
    checks.append(("SQLite DB", os.path.exists(SQLITE_DB_PATH), SQLITE_DB_PATH))
    return checks


init_state(st.session_state)

with st.sidebar:
    st.subheader("Chats")

    chat_ids = list(st.session_state.chats.keys())
    active = st.session_state.active_chat_id
    idx = chat_ids.index(active) if active in chat_ids else 0

    selected = st.selectbox(
        "Select chat",
        options=chat_ids,
        index=idx,
        format_func=lambda cid: st.session_state.chats[cid]["title"],
    )
    if selected != st.session_state.active_chat_id:
        set_active_chat(st.session_state, selected)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("New chat", use_container_width=True):
            create_chat(st.session_state)
            st.rerun()
    with c2:
        if st.button("Delete", use_container_width=True):
            delete_chat(st.session_state, st.session_state.active_chat_id)
            st.rerun()

    st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
    st.markdown("**Demo guardrails active**")
    st.markdown(
        "<div class='small-note'>Responses are policy-grounded, transformed, and internal details are hidden.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Run health check", use_container_width=True):
        st.session_state["health_report"] = _healthcheck()

    if st.session_state.get("health_report"):
        st.markdown("**Health check**")
        for name, ok, detail in st.session_state["health_report"]:
            badge = "OK" if ok else "Missing"
            st.caption(f"{name}: {badge} ({detail})")

kb_fp = _safe_fingerprint([GUIDE_PATH, PROB_PATH, CSV_PATH])
sql_fp = _safe_fingerprint([CSV_PATH])

if kb_fp is None or sql_fp is None:
    st.stop()

need_kb = True
if os.path.exists(INDEX_MARKER):
    try:
        old = open(INDEX_MARKER, "r", encoding="utf-8").read().strip()
        need_kb = old != kb_fp
    except Exception:
        need_kb = True

if need_kb:
    with st.spinner("Building knowledge index..."):
        try:
            g = load_guidelines_chunks(GUIDE_PATH)
            p = load_problem_chunks(PROB_PATH)
            csv_light = csv_schema_and_sample_text(CSV_PATH, sample_rows=25)
            create_db(g + p + csv_light)

            os.makedirs(os.path.dirname(INDEX_MARKER), exist_ok=True)
            with open(INDEX_MARKER, "w", encoding="utf-8") as f:
                f.write(kb_fp)
        except Exception as err:
            st.error(f"Failed to build vector knowledge base: {err}")
            st.stop()

need_sql = True
if os.path.exists(SQL_MARKER) and os.path.exists(SQLITE_DB_PATH):
    try:
        old = open(SQL_MARKER, "r", encoding="utf-8").read().strip()
        need_sql = old != sql_fp
    except Exception:
        need_sql = True

if need_sql:
    with st.spinner("Preparing analytics database..."):
        try:
            load_csv_to_sqlite(CSV_PATH, SQLITE_DB_PATH, SQLITE_TABLE)
            with open(SQL_MARKER, "w", encoding="utf-8") as f:
                f.write(sql_fp)
        except Exception as err:
            st.error(f"Failed to build SQLite dataset: {err}")
            st.stop()

quick_examples = [
    "Summarize the key policy scope",
    "What are the top risk signals we should monitor?",
    "Give trend-based insights from trade data",
]

st.markdown("<div class='quickbar'>Try one:</div>", unsafe_allow_html=True)
q1, q2, q3 = st.columns(3)
if q1.button(quick_examples[0], use_container_width=True):
    st.session_state["quick_prompt"] = quick_examples[0]
if q2.button(quick_examples[1], use_container_width=True):
    st.session_state["quick_prompt"] = quick_examples[1]
if q3.button(quick_examples[2], use_container_width=True):
    st.session_state["quick_prompt"] = quick_examples[2]

msgs = get_active_messages(st.session_state)
for m in msgs:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_text = st.chat_input("Ask about policy or data insights")
if not user_text and st.session_state.get("quick_prompt"):
    user_text = st.session_state.pop("quick_prompt")

if user_text:
    ok, msg = validate_query(user_text)
    if not ok:
        with st.chat_message("assistant"):
            st.warning(msg)
        add_message(st.session_state, "assistant", msg)
    else:
        add_message(st.session_state, "user", user_text)
        with st.chat_message("user"):
            st.markdown(user_text)

        hist = history_text(get_active_messages(st.session_state), max_turns=8)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                route = route_query(user_text, history=hist)

                try:
                    if route == "DATA":
                        result = answer_with_sql(user_text, SQLITE_DB_PATH, SQLITE_TABLE, history=hist)
                    elif route == "SUMMARY":
                        result = summarize()
                    elif route == "INSIGHT":
                        result = generate_insights()
                    else:
                        result = answer_question(user_text, history=hist)
                except Exception:
                    result = "I hit an internal issue while preparing the answer. Please try again."

                result = filter_output(result)
                st.markdown(result)

        add_message(st.session_state, "assistant", result)
