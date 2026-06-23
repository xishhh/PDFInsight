import logging
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._last_cleanup: float = 0.0

    def _cleanup(self, window_seconds: int) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds * 2
        stale = [k for k, v in self._buckets.items() if not v or max(v) < cutoff]
        for k in stale:
            del self._buckets[k]
        self._last_cleanup = now

    def check(self, key: str, max_requests: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            if now - self._last_cleanup > window_seconds:
                self._cleanup(window_seconds)
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
