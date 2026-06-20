import json
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.schemas import AskRequest, AskResponse, SourceCitation
from app.services.rag_service import answer_question, answer_question_stream

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
        answer, sources_used, sources = answer_question(question)
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
        sources=[SourceCitation(**s) for s in sources],
    )


@router.post("/ask/stream")
async def ask_question_stream(body: AskRequest):
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

    logger.info("Received /ask/stream request: %s", question)

    try:
        stream, sources = answer_question_stream(question)
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Streaming answer generation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Answer generation failed. Check LLM configuration.",
        )

    async def event_stream():
        payload = {
            "sources": sources,
            "tokens": [],
        }
        yield json.dumps(payload, separators=(",", ":"))[:-2]

        for token in stream:
            yield "," + json.dumps(token)

        yield "]}"

    return StreamingResponse(
        event_stream(),
        media_type="application/json",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
        },
    )
