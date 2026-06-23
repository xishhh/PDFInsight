import logging
import re
import threading

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

_bm25: BM25Okapi | None = None
_corpus: list[dict] = []
_is_dirty: bool = True
_lock = threading.Lock()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _rebuild_index(session_id: str = "") -> None:
    global _bm25, _corpus, _is_dirty
    with _lock:
        if not _is_dirty and _bm25 is not None:
            return
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

        _corpus = []
        tokenized_corpus: list[list[str]] = []

        for doc, meta, doc_id in zip(docs, metadatas, ids):
            _corpus.append({
                "chunk_id": doc_id,
                "source": meta.get("filename", ""),
                "content": doc,
                "session_id": meta.get("session_id", ""),
            })
            tokenized_corpus.append(_tokenize(doc))

        if tokenized_corpus:
            _bm25 = BM25Okapi(tokenized_corpus)
        else:
            _bm25 = None

        _is_dirty = False
        logger.info("BM25 index rebuilt with %d documents", len(_corpus))


def mark_dirty() -> None:
    global _is_dirty
    _is_dirty = True
    logger.debug("BM25 index marked dirty — will rebuild on next query")


def search(query: str, top_k: int = 10, session_id: str = "") -> list[dict]:
    global _is_dirty

    if _is_dirty or _bm25 is None:
        _rebuild_index(session_id=session_id)

    if _bm25 is None or not _corpus:
        logger.info("BM25 index is empty — no results")
        return []

    tokenized_query = _tokenize(query)
    scores = _bm25.get_scores(tokenized_query)

    scored = list(zip(scores, _corpus))
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, chunk in scored:
        if session_id and chunk.get("session_id") != session_id:
            continue
        results.append({
            "chunk_id": chunk["chunk_id"],
            "source": chunk["source"],
            "content": chunk["content"],
            "score": float(score),
        })
        if len(results) >= top_k:
            break

    logger.info(
        "BM25 search returned %d results (session=%s)", len(results), session_id
    )
    return results
