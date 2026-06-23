import logging
import uuid

from fastapi import Request, Response

logger = logging.getLogger(__name__)

SESSION_HEADER = "X-Session-ID"
SESSION_QUERY_PARAM = "session_id"


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def get_session_id(request: Request, response: Response) -> str:
    """Read session ID from header, query param, or generate a new one.

    Priority: X-Session-ID header → ?session_id= query param → generate new.
    Query param fallback is critical because HF Spaces proxy strips custom headers.
    """
    # 1. Try header first (works locally and on some proxies)
    session_id = request.headers.get(SESSION_HEADER, "").strip()
    if session_id and _is_valid_uuid(session_id):
        return session_id

    # 2. Try query parameter (guaranteed to survive any proxy)
    session_id = request.query_params.get(SESSION_QUERY_PARAM, "").strip()
    if session_id and _is_valid_uuid(session_id):
        return session_id

    # 3. Generate new session as last resort
    session_id = str(uuid.uuid4())
    response.headers[SESSION_HEADER] = session_id
    logger.info("New session started: %s", session_id)
    return session_id
