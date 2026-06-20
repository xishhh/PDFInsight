import logging

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _model
    if _model is None:
        logger.info("Loading cross-encoder model: %s", RERANKER_MODEL)
        _model = CrossEncoder(RERANKER_MODEL)
        logger.info("Cross-encoder model loaded successfully")
    return _model


def rerank(question: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    if not candidates:
        return []

    model = get_reranker()

    pairs = [(question, c["content"]) for c in candidates]
    scores = model.predict(pairs, show_progress_bar=False)

    scored = list(zip(scores, candidates))
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, chunk in scored[:top_k]:
        results.append({
            "chunk_id": chunk["chunk_id"],
            "source": chunk["source"],
            "content": chunk["content"],
            "relevance_score": float(score),
        })

    logger.info("Reranker returned top %d results", len(results))
    return results
