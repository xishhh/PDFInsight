import logging
import uuid
from datetime import datetime, timezone

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
    return collection


def store_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    source_filename: str,
) -> int:
    collection = get_chroma_collection()
    timestamp = datetime.now(timezone.utc).isoformat()

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {
            "chunk_index": idx,
            "filename": source_filename,
            "uploaded_at": timestamp,
        }
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


def delete_document_chunks(filename: str) -> int:
    collection = get_chroma_collection()
    results = collection.get(where={"filename": filename})
    ids = results.get("ids", [])
    if not ids:
        logger.warning("No chunks found for document: %s", filename)
        return 0

    collection.delete(ids=ids)
    logger.info("Deleted %d chunks for document: %s", len(ids), filename)
    return len(ids)


def list_documents() -> list[dict]:
    collection = get_chroma_collection()
    all_data = collection.get(include=["metadatas"])

    metadatas = all_data.get("metadatas", [])
    ids = all_data.get("ids", [])

    if not metadatas:
        return []

    doc_map: dict[tuple[str, str], dict] = {}
    for meta in metadatas:
        fname = meta.get("filename", "unknown")
        uploaded_at = meta.get("uploaded_at", "")
        key = (fname, uploaded_at)
        if key not in doc_map:
            doc_map[key] = {
                "filename": fname,
                "chunks": 0,
                "uploaded_at": uploaded_at,
            }
        doc_map[key]["chunks"] += 1

    return sorted(doc_map.values(), key=lambda d: (d["filename"], d["uploaded_at"]))
