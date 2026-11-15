import json
import os
import re
import sys
from functools import lru_cache

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.vectorstore import BEDROCK_CONFIG, get_vector_store

load_dotenv()

TOP_K = 4
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "1.5"))
USE_HYBRID = os.getenv("USE_HYBRID", "1") == "1"   # vector + keyword search
USE_GATE = os.getenv("USE_GATE", "1") == "1"       # structured answerability check
RRF_K = 60
BM25_EXTRA = 2   # strongest keyword hits that are always included
VEC_GUARANTEED = 3   # strongest semantic hits that are always included
MAX_CONTEXT = 6      # max chunks sent to the model
NO_INFO = "No relevant information found in historical proposals."

# ---------- Prompts ----------
PROMPT = """You draft answers to RFP (Request for Proposal) questions for NimbusEdge Technologies.

Rules:
1. Use ONLY the information in the context below. Never use outside knowledge or invent facts.
2. After each fact, cite its source file in square brackets, for example [02_information_security_policy.md].
3. If the context does not directly answer the question that was asked, reply with exactly this sentence and nothing else:
{no_info}
4. Use a professional tone suitable for a client proposal. Be concise.
5. When the context answers the question and includes specific figures, metrics or outcomes (percentages, timelines, counts), include them.

Context:
{context}

RFP question: {question}

Answer:"""

GATE_PROMPT = """You draft answers to RFP (Request for Proposal) questions for NimbusEdge Technologies.
Respond with ONE JSON object and nothing else (no markdown fences), with exactly these keys:

{{
  "subject": "the exact subject the question asks about (place, team, product, period, metric)",
  "supporting_quotes": ["verbatim sentences copied from the context that state a fact about that exact subject"],
  "covers_exact_subject": true or false,
  "answer": "the drafted answer, or an empty string if covers_exact_subject is false"
}}

Rules:
1. Use ONLY the context below. Never use outside knowledge or invent facts.
2. covers_exact_subject is true only if the context states a fact about EXACTLY the subject in the question. A fact about a broader group (for example a company-wide figure when the question asks about one office or team), a different place, product or period does not count: set it to false and leave answer empty.
3. supporting_quotes must be copied word for word from the context. If you cannot quote anything, covers_exact_subject is false.
4. In "answer", cite the source file after each fact in square brackets, for example [02_information_security_policy.md]. Use a professional tone, be concise, and include specific figures, metrics or outcomes when the context has them.

Context:
{context}

RFP question: {question}

JSON:"""

# Safety check: fail loudly at startup if a prompt loses its placeholders
for _p, _names in ((PROMPT, ("{context}", "{question}", "{no_info}")),
                   (GATE_PROMPT, ("{context}", "{question}"))):
    for _n in _names:
        assert _n in _p, f"prompt is missing {_n}"


# ---------- LLM ----------
@lru_cache
def get_llm():
    return ChatBedrockConverse(
        model=os.getenv("LLM_MODEL_ID"),
        region_name=os.getenv("AWS_REGION"),
        temperature=0,
        max_tokens=900,
        config=BEDROCK_CONFIG,
    )


def _to_text(content):
    if isinstance(content, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return content


# ---------- Retrieval ----------
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "do", "does",
    "you", "your", "we", "our", "is", "are", "what", "which", "how", "have", "has",
    "it", "this", "that", "by", "at", "as", "be", "from", "can", "will", "any",
}

def _stem(t: str) -> str:
    for suf in ("ions", "ion", "ings", "ing", "ed", "es", "s", "e"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[: -len(suf)]
    return t


def _tokens(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]

def _key(doc) -> tuple:
    return (doc.metadata.get("source"), doc.page_content)


_bm25_cache = {"count": -1, "bm25": None, "docs": []}


def _bm25():
    """Keyword index over every chunk in Chroma. Rebuilt automatically when the chunk count
    changes (e.g. after a document upload), so new uploads are searchable immediately."""
    store = get_vector_store()
    count = store._collection.count()
    if _bm25_cache["count"] != count:
        data = store.get(include=["documents", "metadatas"])
        docs = [Document(page_content=t, metadata=m or {}) for t, m in zip(data["documents"], data["metadatas"])]
        _bm25_cache["docs"] = docs
        _bm25_cache["bm25"] = BM25Okapi([_tokens(d.page_content) or ["_"] for d in docs]) if docs else None
        _bm25_cache["count"] = count
    return _bm25_cache["bm25"], _bm25_cache["docs"]


def vector_search(question: str, k: int = TOP_K):
    return [(d, s, False) for d, s in get_vector_store().similarity_search_with_score(question, k=k)]


def hybrid_search(question: str, k: int = TOP_K):
    """Vector + BM25 keyword search, merged with Reciprocal Rank Fusion.
    Returns (doc, vector_distance, keyword_hit) for the top k chunks."""
    store = get_vector_store()
    total = store._collection.count()
    if total == 0:
        return []

    vec = store.similarity_search_with_score(question, k=total)  # every chunk gets a distance
    vec_rank = {_key(d): r for r, (d, _) in enumerate(vec, 1)}
    dist = {_key(d): s for d, s in vec}
    doc_by_key = {_key(d): d for d, _ in vec}

    bm25, docs = _bm25()
    q = _tokens(question)
    scores = bm25.get_scores(q) if (bm25 and q) else [0.0] * len(docs)
    order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
    bm_rank = {_key(docs[i]): r for r, i in enumerate(order, 1) if scores[i] > 0}

    fused = {}
    for key in doc_by_key:
        score = 1 / (RRF_K + vec_rank[key])
        if key in bm_rank:
            score += 1 / (RRF_K + bm_rank[key])
        fused[key] = score

    vec_top = [_key(d) for d, _ in vec[:VEC_GUARANTEED]]
    kw_top = [key for key, _ in sorted(bm_rank.items(), key=lambda kv: kv[1]) if key in doc_by_key][:BM25_EXTRA]
    final = []
    for key in vec_top + kw_top + sorted(fused, key=fused.get, reverse=True):
        if key not in final:
            final.append(key)
        if len(final) >= MAX_CONTEXT:
            break
    return [(doc_by_key[key], dist[key], bm_rank.get(key, 10**6) <= BM25_EXTRA) for key in final]


# ---------- Answer gate ----------
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _parse_json(text: str):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _gated_answer(prompt: str, context: str):
    """Returns (answer_or_None, debug). None means: refuse with NO_INFO."""
    raw = _to_text(get_llm().invoke(prompt).content)
    data = _parse_json(raw)
    if not data:
        print("WARN: gate returned unparseable output; refusing", file=sys.stderr)
        return None, {"error": "unparseable", "raw": raw[:300]}

    ctx = _norm(context)
    grounded = [q for q in data.get("supporting_quotes", []) if _norm(str(q)) and _norm(str(q)) in ctx]
    debug = {"subject": data.get("subject"), "covers": data.get("covers_exact_subject"),
             "quotes_total": len(data.get("supporting_quotes", [])), "quotes_grounded": len(grounded)}

    if data.get("covers_exact_subject") is not True or not grounded or not str(data.get("answer", "")).strip():
        return None, debug
    return str(data["answer"]).strip(), debug


# ---------- Main entry point ----------
def answer_question(question: str, max_distance: float | None = None) -> dict:
    limit = MAX_DISTANCE if max_distance is None else max_distance

    # 1. Search
    hits = hybrid_search(question) if USE_HYBRID else vector_search(question)
    matches = [{"source": d.metadata["source"], "distance": round(s, 3)} for d, s, _ in hits]

    # 2. Keep chunks that are close in vector space OR matched on keywords
    relevant = [(d, s) for d, s, kw in hits if s <= limit or kw]
    if not relevant:
        return {"answer": NO_INFO, "sources": [], "matches": matches}

    # 3. Build the prompt
    context = "\n\n".join(f"[Source: {d.metadata['source']}]\n{d.page_content}" for d, _ in relevant)

    # 4. Ask the LLM
    debug = None
    if USE_GATE:
        answer, debug = _gated_answer(GATE_PROMPT.format(context=context, question=question), context)
        if answer is None:
            return {"answer": NO_INFO, "sources": [], "matches": matches, "gate": debug}
    else:
        answer = _to_text(get_llm().invoke(PROMPT.format(no_info=NO_INFO, context=context, question=question)).content).strip()
        if NO_INFO.lower() in answer.lower():
            return {"answer": NO_INFO, "sources": [], "matches": matches}

    # Only list files the answer actually cites, so an uncited answer can't look sourced
    files = sorted({d.metadata["source"] for d, _ in relevant})
    cited = [f for f in files if f in answer]
    return {"answer": answer, "sources": cited, "matches": matches, "gate": debug}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What is your data encryption policy?"
    result = answer_question(q)
    print(f"QUESTION: {q}\n")
    print(f"ANSWER:\n{result['answer']}\n")
    print("SOURCES:", result["sources"])
    print("GATE:", result.get("gate"))
    print("SEARCH MATCHES (lower distance = closer):")
    for m in result["matches"]:
        print(f"   {m['distance']}  {m['source']}")