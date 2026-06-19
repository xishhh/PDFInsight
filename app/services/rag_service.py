import logging

from app.services.retrieval_service import retrieve_chunks
from app.services.llm_service import generate_answer

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "I could not find the answer in the provided document."


def build_context(chunks: list[dict]) -> str:
    parts = [chunk["content"] for chunk in chunks]
    return "\n\n".join(parts)


def answer_question(question: str) -> tuple[str, int]:
    logger.info("Retrieving chunks for question: %s", question)
    chunks = retrieve_chunks(question)
    sources_used = len(chunks)

    if sources_used == 0:
        logger.info("No chunks retrieved — returning default message")
        return NOT_FOUND_MESSAGE, 0

    context = build_context(chunks)

    logger.info("Context built (%d chars, %d sources)", len(context), sources_used)
    answer = generate_answer(context, question)

    return answer, sources_used
