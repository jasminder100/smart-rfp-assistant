from langchain_chroma import Chroma
from ingest import get_embeddings, CHROMA_DIR, COLLECTION

db = Chroma(
    collection_name=COLLECTION,
    embedding_function=get_embeddings(),
    persist_directory=CHROMA_DIR,
)

question = "What is your data encryption policy?"
results = db.similarity_search_with_score(question, k=3)

print(f"Question: {question}\n")
for doc, score in results:
    print(f"[distance {score:.3f}]  {doc.metadata['source']}")
    print("   ", doc.page_content[:150].replace("\n", " "), "...\n")