import logging
import uuid

from fastapi import Request, Response

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "session_id"
SESSION_MAX_AGE = 86400 * 365


def get_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            max_age=SESSION_MAX_AGE,
            httponly=True,
            secure=True,
            samesite="lax",
        )
        logger.info("New session started: %s", session_id)
    return session_id
