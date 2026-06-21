import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.models.schemas import DocumentInfo, DocumentListResponse, DeleteResponse
from app.services.session_service import get_session_id
from app.services.vector_store_service import list_documents, delete_document_chunks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
async def get_documents(
    session_id: str = Depends(get_session_id),
):
    logger.info("Listing documents (session=%s)", session_id)
    try:
        docs = list_documents(session_id=session_id)
    except Exception as e:
        logger.error("Failed to list documents: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents",
        )

    return DocumentListResponse(
        documents=[DocumentInfo(**d) for d in docs],
        total=len(docs),
    )


@router.delete("/documents/{filename}", response_model=DeleteResponse)
async def delete_document(
    filename: str,
    session_id: str = Depends(get_session_id),
):
    logger.info("Deleting document: %s (session=%s)", filename, session_id)

    if not filename or not filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty",
        )

    try:
        chunks_deleted = delete_document_chunks(filename, session_id=session_id)
    except Exception as e:
        logger.error("Failed to delete document '%s': %s", filename, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )

    if chunks_deleted == 0:
        logger.warning("Document not found: %s (session=%s)", filename, session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{filename}' not found",
        )

    file_path = Path(settings.UPLOAD_DIR) / Path(filename).name
    if file_path.exists():
        file_path.unlink()
        logger.info("Deleted physical file: %s (session=%s)", file_path, session_id)

    return DeleteResponse(
        status="success",
        filename=filename,
        chunks_deleted=chunks_deleted,
    )
