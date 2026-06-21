import logging
from collections.abc import Generator

from app.core.config import settings
from app.services.hybrid_retrieval_service import hybrid_retrieve
from app.services.llm_service import generate_answer, generate_answer_stream

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "I could not find the answer in the provided document."


def _retrieve_and_prepare(
    question: str, session_id: str = ""
) -> tuple[list[dict], str, list[dict], dict]:
    chunks, stats = hybrid_retrieve(question, session_id=session_id)
    if not chunks:
        return [], "", [], stats
    deduped = _deduplicate_chunks(chunks)
    context = build_context(deduped)
    sources = _extract_sources(deduped)
    return deduped, context, sources, stats


def _deduplicate_chunks(chunks: list[dict], threshold: float = 0.8) -> list[dict]:
    if len(chunks) <= 1:
        return chunks

    result = [chunks[0]]
    for chunk in chunks[1:]:
        tokens_a = set(chunk["content"].lower().split())
        is_near_duplicate = False
        for kept in result:
            tokens_b = set(kept["content"].lower().split())
            if not tokens_a or not tokens_b:
                continue
            jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
            if jaccard > threshold:
                is_near_duplicate = True
                break
        if not is_near_duplicate:
            result.append(chunk)

    if len(result) < len(chunks):
        logger.info(
            "Removed %d near-duplicate chunks via Jaccard dedup",
            len(chunks) - len(result),
        )
    return result


def build_context(chunks: list[dict]) -> str:
    parts = [c["content"] for c in chunks]
    context = "\n\n".join(parts)

    if len(context) > settings.MAX_CONTEXT_CHARS:
        logger.warning(
            "Context length %d exceeds MAX_CONTEXT_CHARS=%d, truncating",
            len(context),
            settings.MAX_CONTEXT_CHARS,
        )
        context = context[: settings.MAX_CONTEXT_CHARS]

    return context


def _extract_sources(chunks: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    sources: list[dict] = []
    for chunk in chunks:
        key = (chunk["source"], chunk["chunk_id"])
        if key not in seen:
            seen.add(key)
            sources.append({
                "filename": chunk["source"],
                "chunk_id": chunk["chunk_id"],
            })
    return sources


def answer_question(question: str, session_id: str = "") -> tuple[str, int, list[dict], dict]:
    logger.info("Answering question: %s (session=%s)", question, session_id)
    chunks, context, sources, stats = _retrieve_and_prepare(question, session_id=session_id)

    if not chunks:
        logger.info("No chunks retrieved — returning default message")
        return NOT_FOUND_MESSAGE, 0, [], stats

    sources_used = len(sources)
    logger.info("Context built (%d chars, %d sources, session=%s)", len(context), sources_used, session_id)

    answer = generate_answer(context, question)
    return answer, sources_used, sources, stats


def answer_question_stream(question: str, session_id: str = "") -> tuple[Generator[str, None, None], list[dict], dict]:
    logger.info("Streaming answer for question: %s (session=%s)", question, session_id)
    chunks, context, sources, stats = _retrieve_and_prepare(question, session_id=session_id)

    if not chunks:
        logger.info("No chunks retrieved — returning default message as stream")

        def empty_gen():
            yield NOT_FOUND_MESSAGE

        return empty_gen(), [], stats

    logger.info("Streaming context built (%d chars, %d sources, session=%s)", len(context), len(sources), session_id)

    stream = generate_answer_stream(context, question)
    return stream, sources, stats
