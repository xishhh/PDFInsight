import logging
import uuid

from fastapi import Request, Response

logger = logging.getLogger(__name__)

SESSION_HEADER = "X-Session-ID"


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def get_session_id(request: Request, response: Response) -> str:
    """Read session ID from the X-Session-ID header.

    If the header is missing or invalid, generate a new UUID and echo it
    back via the X-Session-ID response header so the client can store it.
    This avoids all cookie/proxy/iframe issues on HF Spaces.
    """
    session_id = request.headers.get(SESSION_HEADER, "").strip()

    if session_id and _is_valid_uuid(session_id):
        return session_id

    # Client didn't send a valid session ID — generate one
    session_id = str(uuid.uuid4())
    response.headers[SESSION_HEADER] = session_id
    logger.info("New session started: %s", session_id)
    return session_id
