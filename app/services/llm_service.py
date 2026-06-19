import logging
import time

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


def generate_answer(context: str, question: str) -> str:
    client = get_llm_client()
    logger.info("Sending prompt to LLM (%s)", settings.LLM_MODEL)

    max_retries = 2
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 2):
        try:
            response = client.chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion:\n{question}",
                    },
                ],
                max_tokens=512,
                temperature=0.1,
            )
            answer = response["choices"][0]["message"]["content"]
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

    raise last_error  # type: ignore[misc]
