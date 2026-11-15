import html
import os
import re

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
NO_INFO = "No relevant information found in historical proposals."

EXAMPLES = [
    "What is your data encryption policy?",
    "What availability SLA do you commit to?",
    "Have you migrated banks to the cloud before?",
    "How quickly do you notify clients of a data breach?",
    "What are your RPO and RTO commitments?",
    "What certifications does your company hold?",
]

st.set_page_config(page_title="RFP Response Assistant", layout="centered")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.stApp, .stApp input, .stApp textarea, .stApp button {font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;}
.stApp {background: #F2F5F9;}
header[data-testid="stHeader"] {background: transparent;}
footer {visibility: hidden;}
.block-container {max-width: 900px; padding-top: 1.6rem; padding-bottom: 4rem;}

/* ---------- Hero ---------- */
.hero {background: linear-gradient(120deg, #0B1F3A 0%, #17428A 60%, #2F6FED 100%); border-radius: 16px; padding: 28px 32px; margin-bottom: 22px; box-shadow: 0 8px 24px rgba(11,31,58,.18);}
.hero-eyebrow {font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; color: #9FC2FF; font-weight: 600; margin-bottom: 6px;}
.hero-title {font-size: 1.85rem; font-weight: 700; letter-spacing: -.02em; line-height: 1.15; color: #FFFFFF;}
.hero-sub {color: #C9D9F2; margin-top: 8px; font-size: .98rem; max-width: 640px; line-height: 1.5;}
.hero-pills {margin-top: 16px;}
.hero-pills span {display: inline-block; background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.22); color: #FFFFFF; border-radius: 999px; padding: 4px 12px; font-size: .78rem; margin: 0 8px 6px 0;}

/* ---------- Question box ---------- */
div[data-testid="stForm"] {border: none; padding: 0; background: transparent;}
div[data-baseweb="input"] {background: #FFFFFF; border: 1px solid #C9D3E1; border-radius: 12px; box-shadow: 0 1px 2px rgba(16,24,40,.05);}
div[data-baseweb="input"]:focus-within {border-color: #2F6FED; box-shadow: 0 0 0 3px rgba(47,111,237,.18);}
div[data-baseweb="base-input"] {background: #FFFFFF; border-radius: 12px;}
div[data-baseweb="input"] input {padding: 14px 16px; font-size: 1rem; color: #16212F;}

/* ---------- Example cards (buttons inside columns) ---------- */
div[data-testid="stColumn"] button, div[data-testid="column"] button {width: 100%; min-height: 68px; justify-content: flex-start; text-align: left; background: #FFFFFF; border: 1px solid #DCE3EC; border-radius: 12px; color: #16212F; font-weight: 500; padding: 12px 16px; box-shadow: 0 1px 2px rgba(16,24,40,.04);}
div[data-testid="stColumn"] button p, div[data-testid="column"] button p {text-align: left; white-space: normal;}
div[data-testid="stColumn"] button:hover, div[data-testid="column"] button:hover {border-color: #2F6FED; color: #2F6FED; background: #F7FAFF;}

/* ---------- Submit button (overrides the card style above) ---------- */
div[data-testid="stForm"] div[data-testid="stColumn"] button, div[data-testid="stForm"] div[data-testid="column"] button {background: #2F6FED; color: #FFFFFF; border: none; min-height: 52px; justify-content: center; text-align: center; font-weight: 600; border-radius: 12px; box-shadow: none;}
div[data-testid="stForm"] div[data-testid="stColumn"] button:hover, div[data-testid="stForm"] div[data-testid="column"] button:hover {background: #2459D6; color: #FFFFFF;}
div[data-testid="stForm"] button p {text-align: center; color: #FFFFFF;}

/* ---------- Answer cards ---------- */
.section-label {font-size: .72rem; font-weight: 600; letter-spacing: .09em; text-transform: uppercase; color: #7A8494; margin: 1.4rem 0 .6rem 0;}
.qa {margin-top: 28px;}
.q {display: flex; gap: 10px; align-items: flex-start; font-weight: 600; font-size: 1.02rem; color: #16212F; margin-bottom: 10px;}
.q-tag {background: #16212F; color: #FFFFFF; border-radius: 6px; font-size: .72rem; padding: 2px 7px; margin-top: 3px;}
.card {background: #FFFFFF; border: 1px solid #DCE3EC; border-left-width: 4px; border-radius: 12px; padding: 18px 22px; box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 4px 14px rgba(16,24,40,.05); color: #16212F; line-height: 1.6;}
.card.answer {border-left-color: #12B5A6;}
.card.refusal {border-left-color: #E0A030; background: #FFFBF2;}
.card.error {border-left-color: #D64545; background: #FFF5F5;}
.card-label {font-size: .7rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 8px;}
.answer .card-label {color: #0C8F83;}
.refusal .card-label {color: #A8741A;}
.error .card-label {color: #B03030;}
.card p {margin: 0 0 .6rem 0;}
.card ul, .card ol {margin: 0 0 .6rem 1.1rem; padding: 0;}
.card li {margin-bottom: .3rem;}
.refusal-text {font-weight: 600;}
.muted {color: #6B7788; font-size: .9rem;}
.cite {display: inline-block; background: #E6F5F3; color: #0C8F83; border-radius: 4px; padding: 0 6px; font-size: .76rem; font-family: ui-monospace, Menlo, monospace; vertical-align: 1px;}
.sources {margin-top: 12px; padding-top: 12px; border-top: 1px solid #EDF1F6; font-size: .8rem; color: #6B7788;}
.sources .cite {margin-left: 6px; background: #EEF3FB; color: #2250B5;}
div[data-testid="stExpander"] {background: #FFFFFF; border: 1px solid #DCE3EC; border-radius: 10px; margin-top: 8px;}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {background: #0B1F3A;}
section[data-testid="stSidebar"] * {color: #D5DFEE;}
section[data-testid="stSidebar"] .brand {display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.05rem; color: #FFFFFF; margin-bottom: 1.6rem;}
section[data-testid="stSidebar"] .brand-mark {width: 30px; height: 30px; border-radius: 8px; background: linear-gradient(135deg, #12B5A6, #2F6FED); display: inline-flex; align-items: center; justify-content: center; font-size: .9rem; color: #FFFFFF;}
section[data-testid="stSidebar"] .section-label {color: #8FA6C6; margin: 1.6rem 0 .5rem 0;}
section[data-testid="stSidebar"] .status {display: flex; align-items: center; gap: 8px; font-size: .9rem;}
.dot {width: 8px; height: 8px; border-radius: 50%; display: inline-block;}
.dot.ok {background: #3DD6A5;}
.dot.bad {background: #FF7A7A;}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {background: rgba(255,255,255,.06); border: 1px dashed rgba(255,255,255,.3); border-radius: 10px;}
section[data-testid="stSidebar"] button {background: transparent; border: 1px solid rgba(255,255,255,.3); border-radius: 8px;}
section[data-testid="stSidebar"] button * {color: #FFFFFF;}
section[data-testid="stSidebar"] button[kind="primary"], section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {background: #12B5A6 !important; border-color: #12B5A6 !important;}
section[data-testid="stSidebar"] hr {border-color: rgba(255,255,255,.14);}
section[data-testid="stSidebar"] .note {font-size: .78rem; line-height: 1.5; color: #8FA6C6; margin-top: 1.4rem;}

/* ---------- Alignment fixes ---------- */
div[data-testid="stForm"] div[data-baseweb="input"] {min-height: 52px !important;}
div[data-testid="stForm"] div[data-baseweb="base-input"] {min-height: 52px !important;}
div[data-testid="stForm"] input {padding: 14px 16px !important; font-size: 1rem !important;}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] {width: 100% !important;}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button {width: 100% !important; height: 52px !important; min-height: 52px !important; padding: 0 12px !important;}
div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {align-items: flex-start;}
div[data-testid="stColumn"] div[data-testid="stButton"], div[data-testid="column"] div[data-testid="stButton"] {width: 100% !important;}
div[data-testid="stColumn"] div[data-testid="stButton"] > button, div[data-testid="column"] div[data-testid="stButton"] > button {width: 100% !important; height: 76px !important;}

/* ---------- Round 2 fixes ---------- */
div[data-testid="InputInstructions"] {display: none !important;}
div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {width: 100% !important; gap: 12px !important;}
div[data-testid="stForm"] div[data-testid="stColumn"]:first-child, div[data-testid="stForm"] div[data-testid="column"]:first-child {flex: 5 1 0 !important; min-width: 0 !important; width: auto !important;}
div[data-testid="stForm"] div[data-testid="stColumn"]:last-child, div[data-testid="stForm"] div[data-testid="column"]:last-child {flex: 1 1 0 !important; min-width: 120px !important; width: auto !important;}
.cite-n {display: inline-block; min-width: 16px; padding: 0 4px; margin-left: 3px; background: #E6F5F3; color: #0C8F83; border-radius: 4px; font-size: .68rem; font-weight: 700; line-height: 1.5; text-align: center; vertical-align: super;}
.sources .cite b {color: #0C8F83; margin-right: 2px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []


# ---------------- Helpers ----------------
CITE = re.compile(r"\[(?:Source:\s*)?([\w\-.]+\.(?:md|pdf|txt))\]")


_CITE_NUMS = {}


def _cite(m):
    n = _CITE_NUMS.setdefault(m.group(1), len(_CITE_NUMS) + 1)
    return f'<sup class="cite-n">{n}</sup>'


def inline(text):
    text = html.escape(text)
    text = CITE.sub(_cite, text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def md_to_html(text):
    """Tiny markdown converter: paragraphs, bullet and numbered lists, bold, citation chips."""
    out, items, kind = [], [], None

    def flush():
        nonlocal items, kind
        if items:
            out.append(f"<{kind}>" + "".join(f"<li>{i}</li>" for i in items) + f"</{kind}>")
        items, kind = [], None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            flush()
            continue
        bullet = re.match(r"^[-*\u2022]\s+(.*)", line)
        number = re.match(r"^\d+[.)]\s+(.*)", line)
        if bullet or number:
            k = "ul" if bullet else "ol"
            if kind and kind != k:
                flush()
            kind = k
            items.append(inline((bullet or number).group(1)))
        else:
            flush()
            out.append(f"<p>{inline(line)}</p>")
    flush()
    return "".join(out)


def error_text(resp):
    try:
        return resp.json().get("detail", resp.text)
    except ValueError:
        return resp.text


def ask_api(question):
    try:
        resp = requests.post(f"{API_URL}/ask", json={"question": question}, timeout=120)
        if resp.ok:
            data = resp.json()
            return {"content": data["answer"], "sources": data["sources"], "matches": data["matches"]}
        return {"content": f"The request failed: {error_text(resp)}", "error": True}
    except requests.RequestException as e:
        return {"content": f"Could not reach the API: {e}", "error": True}


def render_entry(entry):
    q, a = entry["q"], entry["a"]
    if a.get("error"):
        kind, label = "error", "Something went wrong"
        body = f'<p>{html.escape(a["content"])}</p>'
    elif a["content"] == NO_INFO:
        kind, label = "refusal", "No match"
        body = (
            f'<p class="refusal-text">{NO_INFO}</p>'
            '<p class="muted">The indexed documents do not cover this question, so nothing was drafted. '
            "Try rephrasing it, or add the relevant proposal from the sidebar.</p>"
        )
    else:
        kind, label = "answer", "Drafted answer"
        _CITE_NUMS.clear()
        body = md_to_html(a["content"])

    sources = ""
    if a.get("sources"):
        chips = "".join(
            f'<span class="cite"><b>{_CITE_NUMS.get(src, i + 1)}</b>&nbsp;{html.escape(src)}</span>'
            for i, src in enumerate(a["sources"])
        )
        sources = f'<div class="sources">Sources{chips}</div>'

    st.markdown(
        f'<div class="qa"><div class="q"><span class="q-tag">Q</span><span>{html.escape(q)}</span></div>'
        f'<div class="card {kind}"><div class="card-label">{label}</div>{body}{sources}</div></div>',
        unsafe_allow_html=True,
    )

    if a.get("matches"):
        with st.expander("Retrieval details"):
            st.caption("The closest passages found for this question. A lower distance means a closer match.")
            rows = "\n".join(f"| {m['source']} | {m['distance']} |" for m in a["matches"])
            st.markdown("| Document | Distance |\n|---|---|\n" + rows)


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark">R</span>RFP Assistant</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Status</div>', unsafe_allow_html=True)
    try:
        api_ok = requests.get(f"{API_URL}/health", timeout=3).ok
    except requests.RequestException:
        api_ok = False
    if api_ok:
        st.markdown('<div class="status"><span class="dot ok"></span>API connected</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="status"><span class="dot bad"></span>API not reachable at {html.escape(API_URL)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-label">Add a past proposal</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Past proposal", type=["pdf", "md", "txt"], label_visibility="collapsed")
    if uploaded and st.button("Index document", type="primary"):
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
    if st.button("Clear conversation"):
        st.session_state.history = []
        st.rerun()

    st.markdown(
        '<div class="note">Answers are drafted only from the indexed documents. '
        "Review every answer before it goes into a client response.</div>",
        unsafe_allow_html=True,
    )

# ---------------- Main area ----------------
st.markdown(
    """
<div class="hero">
<div class="hero-eyebrow">Proposal knowledge base</div>
<div class="hero-title">RFP Response Assistant</div>
<div class="hero-sub">Draft answers to client questionnaires from your approved past proposals, with the source document named for every fact.</div>
<div class="hero-pills"><span>Cited sources</span><span>Past proposals only</span><span>Declines when unsure</span></div>
</div>
""".replace("\n", ""),
    unsafe_allow_html=True,
)

with st.form("ask_form", clear_on_submit=True):
    col_q, col_b = st.columns([6, 1.5])
    with col_q:
        typed = st.text_input(
            "Question",
            placeholder="Ask a question from an RFP, e.g. What is your data encryption policy?",
            label_visibility="collapsed",
        )
    with col_b:
        sent = st.form_submit_button("Draft answer")

question = None
if sent and typed.strip():
    question = typed.strip()
elif st.session_state.get("pending"):
    question = st.session_state.pop("pending")

if question:
    if len(question) < 3:
        st.warning("Please enter a longer question.")
    else:
        with st.spinner("Searching past proposals..."):
            answer = ask_api(question)
        st.session_state.history.insert(0, {"q": question, "a": answer})

if not st.session_state.history:
    st.markdown('<div class="section-label">Common RFP questions</div>', unsafe_allow_html=True)
    for row in range(0, len(EXAMPLES), 3):
        cols = st.columns(3)
        for col, example in zip(cols, EXAMPLES[row:row + 3]):
            with col:
                if st.button(example, key=f"ex_{example}"):
                    st.session_state.pending = example
                    st.rerun()
else:
    for entry in st.session_state.history:
        render_entry(entry)
