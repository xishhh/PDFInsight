import logging

from app.core.config import settings
from app.services.embedding_service import generate_embeddings
from app.services.vector_store_service import get_chroma_collection

logger = logging.getLogger(__name__)


def retrieve_chunks(question: str) -> list[dict]:
    logger.info("Generating embedding for query: %s", question)
    query_embedding = generate_embeddings([question])[0]

    collection = get_chroma_collection()

    logger.info("Querying Chroma with top_k=%d", settings.TOP_K_RESULTS)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=settings.TOP_K_RESULTS,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[dict] = []

    if not results["documents"] or not results["documents"][0]:
        logger.info("No relevant chunks found for query: %s", question)
        return chunks

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    ids = results["ids"][0]

    seen_content: set[str] = set()
    for doc, meta, doc_id in zip(documents, metadatas, ids):
        if doc in seen_content:
            logger.debug("Skipping duplicate chunk: %s", doc[:50])
            continue
        seen_content.add(doc)

        chunks.append({
            "chunk_id": doc_id,
            "source": meta.get("filename", ""),
            "content": doc,
        })

    logger.info("Retrieved %d unique chunks for query: %s", len(chunks), question)
    return chunks
