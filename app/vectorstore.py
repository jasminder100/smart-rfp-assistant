import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from botocore.config import Config

# Retry throttled Bedrock calls patiently instead of failing
BEDROCK_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"}, read_timeout=60)

load_dotenv()

CHROMA_DIR = "chroma_db"
COLLECTION = "rfp_docs"


def get_embeddings():
    return BedrockEmbeddings(
        model_id=os.getenv("EMBED_MODEL_ID"),
        region_name=os.getenv("AWS_REGION"),
        model_kwargs={"dimensions": 512, "normalize": True},
        config=BEDROCK_CONFIG,
    )


@lru_cache
def get_vector_store():
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )