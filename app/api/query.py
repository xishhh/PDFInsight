import logging

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import QueryRequest, QueryResponse, ChunkResult
from app.services.retrieval_service import retrieve_chunks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_documents(body: QueryRequest):
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

    logger.info("Incoming query: %s", question)

    try:
        chunks = retrieve_chunks(question)
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
