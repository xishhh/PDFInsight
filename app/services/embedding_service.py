import logging

from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
    return _model


def generate_embeddings(chunks: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    logger.info("Generating embeddings for %d chunks", len(chunks))
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()
    logger.info("Generated %d embeddings", len(embeddings))
    return embeddings
