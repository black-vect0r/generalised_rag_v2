import uuid
from typing import Dict, List, TypedDict

class Message(TypedDict):
    role: str   # "user" or "assistant"
    content: str

def new_chat_id() -> str:
    return uuid.uuid4().hex[:8]

def init_state(session_state) -> None:
    if "chats" not in session_state:
        # chats: {chat_id: {"title": str, "messages": [Message, ...]}}
        session_state.chats = {}

    if "active_chat_id" not in session_state:
        cid = new_chat_id()
        session_state.chats[cid] = {"title": f"Chat {len(session_state.chats)+1}", "messages": []}
        session_state.active_chat_id = cid

def create_chat(session_state) -> str:
    cid = new_chat_id()
    session_state.chats[cid] = {"title": f"Chat {len(session_state.chats)+1}", "messages": []}
    session_state.active_chat_id = cid
    return cid

def delete_chat(session_state, chat_id: str) -> None:
    if chat_id in session_state.chats:
        del session_state.chats[chat_id]

    # Choose another chat if needed
    if not session_state.chats:
        cid = new_chat_id()
        session_state.chats[cid] = {"title": "Chat 1", "messages": []}
        session_state.active_chat_id = cid
    else:
        session_state.active_chat_id = next(iter(session_state.chats.keys()))

def get_active_messages(session_state) -> List[Message]:
    cid = session_state.active_chat_id
    return session_state.chats[cid]["messages"]

def set_active_chat(session_state, chat_id: str) -> None:
    if chat_id in session_state.chats:
        session_state.active_chat_id = chat_id

def add_message(session_state, role: str, content: str) -> None:
    msgs = get_active_messages(session_state)
    msgs.append({"role": role, "content": content})

def history_text(messages: List[Message], max_turns: int = 8) -> str:
    """
    Convert last N turns into a compact plain-text history.
    max_turns counts user+assistant pairs; we take last 2*max_turns messages.
    """
    tail = messages[-2 * max_turns :] if max_turns > 0 else messages
    lines = []
    for m in tail:
        r = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{r}: {m['content']}")
    return "\n".join(lines).strip()