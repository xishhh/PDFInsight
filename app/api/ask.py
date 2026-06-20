import json
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.schemas import AskRequest, AskResponse, RetrievalStats, SourceCitation
from app.services.rag_service import answer_question, answer_question_stream

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_retrieval_stats(stats: dict) -> RetrievalStats | None:
    if not stats:
        return None
    return RetrievalStats(
        vector_candidates=stats.get("vector_candidates", 0),
        bm25_candidates=stats.get("bm25_candidates", 0),
        reranked_chunks=stats.get("reranked_chunks", 0),
    )


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
        answer, sources_used, sources, stats = answer_question(question)
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
        retrieval_stats=_build_retrieval_stats(stats),
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
        stream, sources, stats = answer_question_stream(question)
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

    retrieval_stats = _build_retrieval_stats(stats)

    async def event_stream():
        initial = {
            "sources": sources,
            "tokens": [],
        }
        if retrieval_stats:
            initial["retrieval_stats"] = retrieval_stats.model_dump()
        yield json.dumps(initial, separators=(",", ":"))[:-2]

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
