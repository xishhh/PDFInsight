import logging
import time

from app.core.config import settings
from app.services.bm25_service import search as bm25_search
from app.services.embedding_service import generate_embeddings
from app.services.reranker_service import rerank
from app.services.vector_store_service import get_chroma_collection

logger = logging.getLogger(__name__)


def hybrid_retrieve(question: str, session_id: str = "") -> tuple[list[dict], dict]:
    seen_content: set[str] = set()
    candidates: list[dict] = []
    stats: dict = {}

    t0 = time.perf_counter()
    query_embedding = generate_embeddings([question])[0]
    collection = get_chroma_collection()

    query_kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": settings.VECTOR_TOP_K,
        "include": ["documents", "metadatas", "distances"],
    }
    if session_id:
        query_kwargs["where"] = {"session_id": session_id}

    dense_results = collection.query(**query_kwargs)

    dense_count = 0
    if dense_results.get("documents") and dense_results["documents"][0]:
        docs = dense_results["documents"][0]
        metas = dense_results["metadatas"][0]
        ids = dense_results["ids"][0]

        for doc, meta, doc_id in zip(docs, metas, ids):
            if doc not in seen_content:
                seen_content.add(doc)
                candidates.append({
                    "chunk_id": doc_id,
                    "source": meta.get("filename", ""),
                    "content": doc,
                })
                dense_count += 1

    t1 = time.perf_counter()
    vector_time = t1 - t0
    stats["vector_search_time"] = round(vector_time, 4)
    stats["vector_candidates"] = dense_count
    logger.info(
        "Vector search: %d candidates in %.4fs (session=%s)",
        dense_count, vector_time, session_id,
    )

    t2 = time.perf_counter()
    bm25_results = bm25_search(question, top_k=settings.BM25_TOP_K, session_id=session_id)
    bm25_count = 0
    for chunk in bm25_results:
        if chunk["content"] not in seen_content:
            seen_content.add(chunk["content"])
            candidates.append(chunk)
            bm25_count += 1

    t3 = time.perf_counter()
    bm25_time = t3 - t2
    stats["bm25_search_time"] = round(bm25_time, 4)
    stats["bm25_candidates"] = bm25_count
    logger.info(
        "BM25 search: %d candidates in %.4fs (session=%s)",
        bm25_count, bm25_time, session_id,
    )

    t4 = time.perf_counter()
    reranked = rerank(question, candidates, top_k=settings.RERANK_TOP_K)
    t5 = time.perf_counter()
    rerank_time = t5 - t4
    stats["rerank_time"] = round(rerank_time, 4)
    stats["reranked_chunks"] = len(reranked)
    logger.info(
        "Reranker: %d results in %.4fs",
        len(reranked), rerank_time,
    )

    total = (t1 - t0) + (t3 - t2) + (t5 - t4)
    stats["total_retrieval_time"] = round(total, 4)
    logger.info("Total retrieval time: %.4fs (session=%s)", total, session_id)

    return reranked, stats
