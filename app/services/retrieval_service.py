import logging

from app.services.hybrid_retrieval_service import hybrid_retrieve

logger = logging.getLogger(__name__)


def retrieve_chunks(question: str) -> list[dict]:
    chunks, _ = hybrid_retrieve(question)
    return chunks
