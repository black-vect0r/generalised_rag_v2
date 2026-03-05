import os
import hashlib
import streamlit as st

from rag.data_loader import (
    load_guidelines_chunks,
    load_problem_chunks,
    csv_schema_and_sample_text,
)
from rag.vector_store import create_db
from rag.sqlite_store import load_csv_to_sqlite

from agents.router_agent import route_query
from agents.qa_agent import answer_question
from agents.summarizer_agent import summarize
from agents.insight_agent import generate_insights
from agents.sql_agent import answer_with_sql

from guardrails.input_guard import validate_query
from guardrails.output_guard import filter_output

from chat.session_store import (
    init_state, create_chat, delete_chat, set_active_chat,
    get_active_messages, add_message, history_text
)

st.set_page_config(page_title="Policy-Aware Multi-Agent RAG (SQLite)")
st.title("🚀 Policy-Aware Multi-Agent RAG System (SQLite)")

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

# ---------- Initialize multi-chat memory ----------
init_state(st.session_state)

# ---------- Sidebar: chat controls ----------
with st.sidebar:
    st.header("Chats")

    chat_ids = list(st.session_state.chats.keys())
    labels = [st.session_state.chats[cid]["title"] for cid in chat_ids]

    # current selection index
    active = st.session_state.active_chat_id
    try:
        idx = chat_ids.index(active)
    except ValueError:
        idx = 0

    selected = st.selectbox("Select chat", options=chat_ids, index=idx, format_func=lambda cid: st.session_state.chats[cid]["title"])
    if selected != st.session_state.active_chat_id:
        set_active_chat(st.session_state, selected)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ New chat", use_container_width=True):
            create_chat(st.session_state)
            st.rerun()
    with col2:
        if st.button("🗑️ Delete chat", use_container_width=True):
            delete_chat(st.session_state, st.session_state.active_chat_id)
            st.rerun()

    st.caption("Tip: Use New chat for a clean demo scenario.")

# ---------- Build / reuse VECTOR index ----------
kb_fp = _fingerprint([GUIDE_PATH, PROB_PATH, CSV_PATH])

need_kb = True
if os.path.exists(INDEX_MARKER):
    try:
        old = open(INDEX_MARKER, "r", encoding="utf-8").read().strip()
        need_kb = (old != kb_fp)
    except Exception:
        need_kb = True

if need_kb:
    with st.spinner("Building policy knowledge base (RAG)..."):
        g = load_guidelines_chunks(GUIDE_PATH)
        p = load_problem_chunks(PROB_PATH)
        csv_light = csv_schema_and_sample_text(CSV_PATH, sample_rows=25)
        create_db(g + p + csv_light)

        os.makedirs(os.path.dirname(INDEX_MARKER), exist_ok=True)
        with open(INDEX_MARKER, "w", encoding="utf-8") as f:
            f.write(kb_fp)

    st.success("RAG knowledge base ready ✅")
else:
    st.info("RAG knowledge base already indexed ✅")

# ---------- Build / reuse SQLITE DB ----------
sql_fp = _fingerprint([CSV_PATH])

need_sql = True
if os.path.exists(SQL_MARKER) and os.path.exists(SQLITE_DB_PATH):
    try:
        old = open(SQL_MARKER, "r", encoding="utf-8").read().strip()
        need_sql = (old != sql_fp)
    except Exception:
        need_sql = True

if need_sql:
    with st.spinner("Loading CSV into SQLite (fast analytics)..."):
        load_csv_to_sqlite(CSV_PATH, SQLITE_DB_PATH, SQLITE_TABLE)
        with open(SQL_MARKER, "w", encoding="utf-8") as f:
            f.write(sql_fp)
    st.success("SQLite dataset ready ✅")
else:
    st.info("SQLite dataset already prepared ✅")

st.divider()

# ---------- Render chat history ----------
msgs = get_active_messages(st.session_state)
for m in msgs:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------- Chat input ----------
user_text = st.chat_input("Ask a question (policy + data supported)")

if user_text:
    ok, msg = validate_query(user_text)
    if not ok:
        with st.chat_message("assistant"):
            st.error(msg)
        add_message(st.session_state, "assistant", msg)
    else:
        add_message(st.session_state, "user", user_text)
        with st.chat_message("user"):
            st.markdown(user_text)

        # build compact history for routing + follow-ups
        hist = history_text(get_active_messages(st.session_state), max_turns=8)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                route = route_query(user_text, history=hist)

                if route == "DATA":
                    result = answer_with_sql(user_text, SQLITE_DB_PATH, SQLITE_TABLE, history=hist)
                elif route == "SUMMARY":
                    result = summarize()
                elif route == "INSIGHT":
                    result = generate_insights()
                else:
                    result = answer_question(user_text, history=hist)

                result = filter_output(result)
                st.markdown(result)

        add_message(st.session_state, "assistant", result)