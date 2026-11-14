import os
import sys
from functools import lru_cache

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

from app.vectorstore import BEDROCK_CONFIG,get_vector_store

load_dotenv()

TOP_K = 4
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "1.5"))
NO_INFO = "No relevant information found in historical proposals."

PROMPT = """You draft answers to RFP (Request for Proposal) questions for NimbusEdge Technologies.

Rules:
1. Use ONLY the information in the context below. Never use outside knowledge or invent facts.
2. After each fact, cite its source file in square brackets, for example [02_information_security_policy.md].
3. If the context does not answer the question, reply with exactly this sentence and nothing else:
{no_info}
4. Use a professional tone suitable for a client proposal. Be concise.
5. When the context includes specific figures, metrics or outcomes (percentages, timelines, counts), include them. Clients evaluating proposals look for concrete evidence.
Context:
{context}

RFP question: {question}

Answer:"""

# Safety check: fail loudly at startup if the prompt ever loses its placeholders again
for placeholder in ("{context}", "{question}", "{no_info}"):
    assert placeholder in PROMPT, f"PROMPT is missing {placeholder}"


@lru_cache
def get_llm():
    return ChatBedrockConverse(
        model=os.getenv("LLM_MODEL_ID"),
        region_name=os.getenv("AWS_REGION"),
        temperature=0,
        max_tokens=600,
        config=BEDROCK_CONFIG,
    )


def _to_text(content):
    if isinstance(content, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return content


def answer_question(question: str, max_distance: float | None = None) -> dict:
    
    limit = MAX_DISTANCE if max_distance is None else max_distance
    # 1. Search
    results = get_vector_store().similarity_search_with_score(question, k=TOP_K)
    matches = [{"source": d.metadata["source"], "distance": round(s, 3)} for d, s in results]

    # 2. Filter out chunks that are too far away
    relevant = [(d, s) for d, s in results if s <= limit]
    if not relevant:
        return {"answer": NO_INFO, "sources": [], "matches": matches}

    # 3. Build the prompt
    context = "\n\n".join(f"[Source: {d.metadata['source']}]\n{d.page_content}" for d, _ in relevant)
    prompt = PROMPT.format(no_info=NO_INFO, context=context, question=question)

    # 4. Ask the LLM
    answer = _to_text(get_llm().invoke(prompt).content).strip()
    if NO_INFO.lower() in answer.lower():
        return {"answer": NO_INFO, "sources": [], "matches": matches}

    # Only list files the answer actually cites, so an uncited answer can't look sourced
    files = sorted({d.metadata["source"] for d, _ in relevant})
    cited = [f for f in files if f in answer]
    return {"answer": answer, "sources": cited, "matches": matches}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What is your data encryption policy?"
    result = answer_question(q)
    print(f"QUESTION: {q}\n")
    print(f"ANSWER:\n{result['answer']}\n")
    print("SOURCES:", result["sources"])
    print("SEARCH MATCHES (lower distance = closer):")
    for m in result["matches"]:
        print(f"   {m['distance']}  {m['source']}")