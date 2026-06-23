import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import validate_question
from app.models.schemas import AskRequest, AskResponse, RetrievalStats, SourceCitation
from app.core.config import settings
from app.services.rag_service import answer_question, answer_question_stream
from app.services.rate_limiter import check_question_rate
from app.services.session_service import get_session_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_retrieval_stats(stats: dict | None) -> RetrievalStats | None:
    if not stats:
        return None
    return RetrievalStats(
        vector_candidates=stats.get("vector_candidates", 0),
        bm25_candidates=stats.get("bm25_candidates", 0),
        reranked_chunks=stats.get("reranked_chunks", 0),
        retrieval_latency_ms=round(stats.get("total_retrieval_time", 0) * 1000, 1),
        rerank_latency_ms=round(stats.get("rerank_time", 0) * 1000, 1),
        llm_latency_ms=stats.get("llm_time_ms"),
    )


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: Request,
    body: AskRequest,
    session_id: str = Depends(get_session_id),
):
    check_question_rate(request, settings.QUESTION_RATE_LIMIT)
    question = validate_question(body.question)
    logger.info("Received /ask request: %s (session=%s)", question, session_id)

    try:
        _llm_start = time.perf_counter()
        answer, sources_used, sources, stats = answer_question(question, session_id=session_id)
        _llm_elapsed = round((time.perf_counter() - _llm_start) * 1000, 1)
        if stats:
            stats["llm_time_ms"] = _llm_elapsed
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
async def ask_question_stream(
    request: Request,
    body: AskRequest,
    session_id: str = Depends(get_session_id),
):
    check_question_rate(request, settings.QUESTION_RATE_LIMIT)
    question = validate_question(body.question)
    logger.info("Received /ask/stream request: %s (session=%s)", question, session_id)

    try:
        stream, sources, stats = await answer_question_stream(question, session_id=session_id)
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
        }
        if retrieval_stats:
            initial["retrieval_stats"] = retrieval_stats.model_dump()

        yield json.dumps(initial, separators=(",", ":"))
        yield ',"tokens":['

        i = 0
        async for token in stream:
            if i > 0:
                yield ","
            yield json.dumps(token)
            i += 1

        yield "]}"

    return StreamingResponse(
        event_stream(),
        media_type="application/json",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
