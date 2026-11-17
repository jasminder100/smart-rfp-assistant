"""Replace app.rag with a stub BEFORE anything imports it, so tests need no AWS, no Chroma, no LLM."""
import sys
import types

fake_rag = types.ModuleType("app.rag")
fake_rag.answer_question = lambda question: {"answer": "stub answer", "sources": []}
sys.modules["app.rag"] = fake_rag