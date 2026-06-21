import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.models.schemas import QuestionRequest, QueryResponse, ChunkResult
from app.services.hybrid_retrieval_service import hybrid_retrieve
from app.services.session_service import get_session_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_question(question: str) -> str:
    stripped = question.strip()
    if not stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty",
        )
    if len(stripped) <= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must be longer than 3 characters",
        )
    return stripped


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    body: QuestionRequest,
    session_id: str = Depends(get_session_id),
):
    question = _validate_question(body.question)

    logger.info("Incoming query: %s (session=%s)", question, session_id)

    try:
        chunks, _ = hybrid_retrieve(question, session_id=session_id)
    except Exception as e:
        logger.error("Retrieval failed for query '%s': %s", question, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Retrieval failed",
        )

    return QueryResponse(
        question=question,
        results_found=len(chunks),
        chunks=[ChunkResult(**c) for c in chunks],
    )
