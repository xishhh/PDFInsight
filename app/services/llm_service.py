import logging
import time
from collections.abc import Generator

from huggingface_hub import InferenceClient

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: InferenceClient | None = None


def get_llm_client() -> InferenceClient:
    global _client
    if _client is None:
        if not settings.HF_API_KEY:
            raise ValueError(
                "HF_API_KEY is not set. Please add it to your .env file."
            )
        logger.info("Initializing Hugging Face Inference API client")
        _client = InferenceClient(
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


def generate_answer(context: str, question: str) -> str:
    client = get_llm_client()
    logger.info("Sending prompt to LLM (%s)", settings.LLM_MODEL)

    max_retries = 2
    last_error: Exception | None = None

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
            last_error = e
            error_str = str(e).lower()

            if "rate limit" in error_str or "429" in error_str:
                wait = 2 ** attempt
                logger.warning(
                    "Rate limited. Retrying in %ds (attempt %d/%d)",
                    wait, attempt, max_retries + 1,
                )
                time.sleep(wait)
                continue

            if attempt <= max_retries:
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s",
                    attempt, max_retries + 1, e,
                )
                time.sleep(1)
                continue

            logger.error("LLM call failed after all retries: %s", e)
            raise

    raise last_error


def generate_answer_stream(context: str, question: str) -> Generator[str, None, None]:
    client = get_llm_client()
    logger.info("Starting streaming LLM call (%s)", settings.LLM_MODEL)

    max_retries = 2
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 2):
        try:
            stream = client.chat_completion(
                messages=_build_messages(context, question),
                max_tokens=512,
                temperature=0.1,
                stream=True,
            )

            for chunk in stream:
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
            last_error = e
            error_str = str(e).lower()

            if "rate limit" in error_str or "429" in error_str:
                wait = 2 ** attempt
                logger.warning(
                    "Rate limited. Retrying in %ds (attempt %d/%d)",
                    wait, attempt, max_retries + 1,
                )
                time.sleep(wait)
                continue

            if attempt <= max_retries:
                logger.warning(
                    "Streaming LLM call failed (attempt %d/%d): %s",
                    attempt, max_retries + 1, e,
                )
                time.sleep(1)
                continue

            logger.error("Streaming LLM call failed after all retries: %s", e)
            raise

    raise last_error
