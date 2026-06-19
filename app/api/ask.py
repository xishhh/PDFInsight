import logging

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import AskRequest, AskResponse
from app.services.rag_service import answer_question

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask_question(body: AskRequest):
    question = body.question.strip()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty",
        )

    if len(question) <= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must be longer than 3 characters",
        )

    logger.info("Received /ask request: %s", question)

    try:
        answer, sources_used = answer_question(question)
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Answer generation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Answer generation failed. Check LLM configuration.",
        )

    return AskResponse(
        question=question,
        answer=answer,
        sources_used=sources_used,
    )
