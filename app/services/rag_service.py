import logging
from collections.abc import Generator

from app.core.config import settings
from app.services.retrieval_service import retrieve_chunks
from app.services.llm_service import generate_answer, generate_answer_stream

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "I could not find the answer in the provided document."


def build_context(chunks: list[dict]) -> str:
    parts = [chunk["content"] for chunk in chunks]
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
    logger.info("Extracted %d source citations from %d chunks", len(sources), len(chunks))
    return sources


def answer_question(question: str) -> tuple[str, int, list[dict]]:
    logger.info("Retrieving chunks for question: %s", question)
    chunks = retrieve_chunks(question)
    sources = _extract_sources(chunks)
    sources_used = len(sources)

    if sources_used == 0:
        logger.info("No chunks retrieved — returning default message")
        return NOT_FOUND_MESSAGE, 0, []

    context = build_context(chunks)
    logger.info("Context built (%d chars, %d sources)", len(context), sources_used)

    answer = generate_answer(context, question)
    return answer, sources_used, sources


def answer_question_stream(question: str) -> tuple[Generator[str, None, None], list[dict]]:
    logger.info("Retrieving chunks for streaming question: %s", question)
    chunks = retrieve_chunks(question)
    sources = _extract_sources(chunks)

    if not sources:
        logger.info("No chunks retrieved — returning default message as stream")

        def empty_gen():
            yield NOT_FOUND_MESSAGE

        return empty_gen(), []

    context = build_context(chunks)
    logger.info("Streaming context built (%d chars, %d sources)", len(context), len(sources))

    stream = generate_answer_stream(context, question)
    return stream, sources
