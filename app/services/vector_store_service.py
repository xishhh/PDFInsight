import logging
import uuid
from datetime import datetime, timezone

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "documents"

_client = None
_collection = None


def get_chroma_collection():
    global _client, _collection
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def store_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    source_filename: str,
    session_id: str = "",
) -> int:
    from app.services.bm25_service import mark_dirty
    collection = get_chroma_collection()
    timestamp = datetime.now(timezone.utc).isoformat()

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {
            "chunk_index": idx,
            "filename": source_filename,
            "uploaded_at": timestamp,
            "session_id": session_id,
        }
        for idx in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    mark_dirty()

    logger.info(
        "Inserted %d chunks into Chroma (session=%s, source=%s)",
        len(chunks), session_id, source_filename,
    )
    return len(chunks)


def delete_document_chunks(filename: str, session_id: str = "") -> int:
    from app.services.bm25_service import mark_dirty
    collection = get_chroma_collection()

    filters: list[dict] = [{"filename": filename}]
    if session_id:
        filters.append({"session_id": session_id})
    where_clause = {"$and": filters} if len(filters) > 1 else filters[0]

    results = collection.get(where=where_clause)
    ids = results.get("ids", [])
    if not ids:
        logger.warning("No chunks found for document: %s (session=%s)", filename, session_id)
        return 0

    collection.delete(ids=ids)
    mark_dirty()
    logger.info("Deleted %d chunks for document: %s (session=%s)", len(ids), filename, session_id)
    return len(ids)


def list_documents(session_id: str = "") -> list[dict]:
    collection = get_chroma_collection()
    where_clause: dict | None = None
    if session_id:
        where_clause = {"session_id": session_id}
    all_data = collection.get(include=["metadatas"], where=where_clause)

    metadatas = all_data.get("metadatas", [])

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
