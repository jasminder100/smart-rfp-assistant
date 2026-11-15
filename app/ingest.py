from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.vectorstore import get_vector_store

DOCS_DIR = Path("data/sample_docs")
SUPPORTED = {".pdf", ".md", ".txt"}


def load_file(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(str(path))
    elif suffix in {".md", ".txt"}:
        loader = TextLoader(str(path), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    docs = loader.load()
    for d in docs:
        d.metadata["source"] = path.name
    return docs


def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=60)
    return splitter.split_documents(docs)


def add_file(path: Path) -> int:
    """Index one file. If it was indexed before, its old chunks are replaced."""
    db = get_vector_store()
    old_ids = db.get(where={"source": path.name})["ids"]
    if old_ids:
        db.delete(ids=old_ids)
    chunks = split_documents(load_file(path))
    if chunks:
        db.add_documents(chunks)
    return len(chunks)


def ingest_folder(folder: Path = DOCS_DIR) -> int:
    total = 0
    for path in sorted(folder.iterdir()):
        if path.name.startswith(".") or path.suffix.lower() not in SUPPORTED:
            continue
        n = add_file(path)
        total += n
        print(f"Indexed {path.name}: {n} chunks")
    return total