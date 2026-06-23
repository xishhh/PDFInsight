import asyncio
import logging
import time
from collections.abc import AsyncGenerator

from huggingface_hub import AsyncInferenceClient, InferenceClient

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncInferenceClient | None = None


def get_llm_client() -> AsyncInferenceClient:
    global _client
    if _client is None:
        if not settings.HF_API_KEY:
            raise ValueError(
                "HF_API_KEY is not set. Please add it to your .env file."
            )
        logger.info("Initializing Hugging Face Inference API client")
        _client = AsyncInferenceClient(
            model=settings.LLM_MODEL,
            token=settings.HF_API_KEY,
            timeout=settings.LLM_TIMEOUT,
        )
    return _client


SYSTEM_PROMPT = """You are a helpful assistant.

Answer ONLY using the provided context.

If the answer cannot be found in the context, respond with:

"I could not find the answer in the provided document."
"""


def _build_messages(context: str, question: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion:\n{question}",
        },
    ]


def _should_retry(e: Exception, attempt: int, max_retries: int) -> tuple[bool, float]:
    error_str = str(e).lower()
    if "rate limit" in error_str or "429" in error_str:
        return True, 2.0 ** attempt
    if attempt <= max_retries:
        return True, 1.0
    return False, 0.0


def generate_answer(context: str, question: str) -> str:
    client = InferenceClient(
        model=settings.LLM_MODEL,
        token=settings.HF_API_KEY,
        timeout=settings.LLM_TIMEOUT,
    )
    logger.info("Sending prompt to LLM (%s)", settings.LLM_MODEL)

    max_retries = 2
    for attempt in range(1, max_retries + 2):
        try:
            response = client.chat_completion(
                messages=_build_messages(context, question),
                max_tokens=512,
                temperature=0.1,
            )
            choices = response.get("choices", [])
            if not choices:
                raise ValueError("LLM returned empty response")
            message = choices[0].get("message", {})
            answer = message.get("content", "")
            if not answer:
                raise ValueError("LLM returned empty content")
            logger.info("LLM response received successfully")
            return answer.strip()

        except Exception as e:
            should_retry, wait = _should_retry(e, attempt, max_retries)
            if not should_retry:
                logger.error("LLM call failed after all retries: %s", e)
                raise
            logger.warning(
                "LLM call failed (attempt %d/%d, retrying in %.1fs): %s",
                attempt, max_retries + 1, wait, e,
            )
            time.sleep(wait)

    raise RuntimeError("Unreachable — retry loop exhausted")


async def generate_answer_stream(context: str, question: str) -> AsyncGenerator[str, None]:
    client = get_llm_client()
    logger.info("Starting streaming LLM call (%s)", settings.LLM_MODEL)

    max_retries = 2
    for attempt in range(1, max_retries + 2):
        try:
            stream = await client.chat_completion(
                messages=_build_messages(context, question),
                max_tokens=512,
                temperature=0.1,
                stream=True,
            )

            async for chunk in stream:
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content

            logger.info("Streaming LLM call completed successfully")
            return

        except Exception as e:
            should_retry, wait = _should_retry(e, attempt, max_retries)
            if not should_retry:
                logger.error("Streaming LLM call failed after all retries: %s", e)
                raise
            logger.warning(
                "Streaming LLM call failed (attempt %d/%d, retrying in %.1fs): %s",
                attempt, max_retries + 1, wait, e,
            )
            await asyncio.sleep(wait)

    raise RuntimeError("Unreachable — retry loop exhausted")
