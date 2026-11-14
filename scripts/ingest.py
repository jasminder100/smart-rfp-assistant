from app.ingest import ingest_folder
from app.vectorstore import get_vector_store

if __name__ == "__main__":
    ingest_folder()
    print(f"\nDone. Total chunks in database: {get_vector_store()._collection.count()}")