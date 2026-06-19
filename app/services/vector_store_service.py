import logging
import uuid

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "documents"


def get_chroma_collection():
    client = chromadb.PersistentClient(
        path=settings.CHROMA_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    logger.info("Using Chroma collection: %s", COLLECTION_NAME)
    return collection


def store_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    source_filename: str,
) -> int:
    collection = get_chroma_collection()

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {"chunk_id": idx, "source": source_filename}
        for idx in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    logger.info(
        "Inserted %d chunks into Chroma (source: %s)", len(chunks), source_filename
    )
    return len(chunks)
