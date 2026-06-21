import logging
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        timestamps = self._buckets[key]
        timestamps[:] = [t for t in timestamps if t > cutoff]

        if len(timestamps) >= max_requests:
            logger.warning(
                "Rate limit exceeded for key=%s (%d/%d per %ds)",
                key, len(timestamps), max_requests, window_seconds,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        timestamps.append(now)


_upload_limiter = RateLimiter()
_question_limiter = RateLimiter()


def check_upload_rate(request: Request, max_requests: int) -> None:
    key = f"upload:{request.client.host}" if request.client else "upload:unknown"
    _upload_limiter.check(key, max_requests)


def check_question_rate(request: Request, max_requests: int) -> None:
    key = f"question:{request.client.host}" if request.client else "question:unknown"
    _question_limiter.check(key, max_requests)
