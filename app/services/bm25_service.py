import logging
import re
import threading

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# Per-session BM25 index cache: session_id -> (BM25Okapi, corpus, dirty)
_index_cache: dict[str, tuple[BM25Okapi | None, list[dict]]] = {}
_global_dirty: bool = True
_lock = threading.Lock()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _rebuild_index(session_id: str = "") -> tuple[BM25Okapi | None, list[dict]]:
    logger.info("Rebuilding BM25 index from ChromaDB (session=%s)...", session_id)

    from app.services.vector_store_service import get_chroma_collection
    collection = get_chroma_collection()
    query_kwargs = {"include": ["documents", "metadatas"]}
    if session_id:
        query_kwargs["where"] = {"session_id": session_id}
    all_data = collection.get(**query_kwargs)

    docs = all_data.get("documents", []) or []
    metadatas = all_data.get("metadatas", []) or []
    ids = all_data.get("ids", []) or []

    corpus: list[dict] = []
    tokenized_corpus: list[list[str]] = []

    for doc, meta, doc_id in zip(docs, metadatas, ids):
        corpus.append({
            "chunk_id": doc_id,
            "source": meta.get("filename", ""),
            "content": doc,
            "session_id": meta.get("session_id", ""),
        })
        tokenized_corpus.append(_tokenize(doc))

    bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None

    logger.info("BM25 index rebuilt with %d documents (session=%s)", len(corpus), session_id)
    return bm25, corpus


def mark_dirty() -> None:
    """Invalidate all cached BM25 indices so they rebuild on next query."""
    global _global_dirty
    with _lock:
        _global_dirty = True
        _index_cache.clear()
    logger.debug("BM25 index marked dirty — will rebuild on next query")


def search(query: str, top_k: int = 10, session_id: str = "") -> list[dict]:
    global _global_dirty

    cache_key = session_id or "__global__"

    with _lock:
        needs_rebuild = _global_dirty or cache_key not in _index_cache
        if needs_rebuild and _global_dirty:
            _global_dirty = False

    if needs_rebuild:
        bm25, corpus = _rebuild_index(session_id=session_id)
        with _lock:
            _index_cache[cache_key] = (bm25, corpus)
    else:
        with _lock:
            bm25, corpus = _index_cache[cache_key]

    if bm25 is None or not corpus:
        logger.info("BM25 index is empty — no results (session=%s)", session_id)
        return []

    tokenized_query = _tokenize(query)
    scores = bm25.get_scores(tokenized_query)

    scored = list(zip(scores, corpus))
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, chunk in scored[:top_k]:
        results.append({
            "chunk_id": chunk["chunk_id"],
            "source": chunk["source"],
            "content": chunk["content"],
            "score": float(score),
        })

    logger.info(
        "BM25 search returned %d results (session=%s)", len(results), session_id
    )
    return results
