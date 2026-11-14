import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
NO_INFO = "No relevant information found in historical proposals."

st.set_page_config(page_title="Smart RFP Assistant", page_icon="📄", layout="wide")

# Chat history survives Streamlit's re-runs because it lives in session_state
if "messages" not in st.session_state:
    st.session_state.messages = []


def error_text(resp):
    """Pull a readable error message out of an API response."""
    try:
        return resp.json().get("detail", resp.text)
    except ValueError:
        return resp.text


def show_answer(msg):
    """Render one assistant answer, with its sources and search details."""
    if msg["content"] == NO_INFO:
        st.info(msg["content"])
    else:
        st.markdown(msg["content"])
    if msg.get("sources"):
        st.markdown("**Sources:** " + ", ".join(f"`{s}`" for s in msg["sources"]))
    if msg.get("matches"):
        with st.expander("Search details (lower distance = closer match)"):
            for m in msg["matches"]:
                st.write(f"`{m['distance']}` — {m['source']}")


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Backend")
    try:
        api_ok = requests.get(f"{API_URL}/health", timeout=3).ok
    except requests.RequestException:
        api_ok = False
    if api_ok:
        st.success("API connected")
    else:
        st.error(f"API not reachable at {API_URL}")

    st.header("Upload a past proposal")
    uploaded = st.file_uploader("PDF, Markdown or text", type=["pdf", "md", "txt"])
    if uploaded and st.button("Add to knowledge base", type="primary"):
        with st.spinner("Reading, chunking and embedding..."):
            try:
                resp = requests.post(
                    f"{API_URL}/upload",
                    files={"file": (uploaded.name, uploaded.getvalue())},
                    timeout=120,
                )
                if resp.ok:
                    data = resp.json()
                    st.success(f"{data['filename']} indexed ({data['chunks_added']} chunks)")
                else:
                    st.error(error_text(resp))
            except requests.RequestException as e:
                st.error(f"Upload failed: {e}")

    st.divider()
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ---------------- Main area ----------------
st.title("📄 Smart RFP Response Assistant")
st.caption("Ask an RFP question. Answers come only from approved past proposals, with sources.")

# Re-draw the conversation so far
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            show_answer(msg)

# New question
if question := st.chat_input("e.g. What is your data encryption policy?"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching past proposals..."):
            try:
                resp = requests.post(f"{API_URL}/ask", json={"question": question}, timeout=120)
                if resp.ok:
                    data = resp.json()
                    msg = {"role": "assistant", "content": data["answer"],
                           "sources": data["sources"], "matches": data["matches"]}
                else:
                    msg = {"role": "assistant", "content": f"⚠️ Error: {error_text(resp)}"}
            except requests.RequestException as e:
                msg = {"role": "assistant", "content": f"⚠️ Could not reach the API: {e}"}
        show_answer(msg)

    st.session_state.messages.append(msg)