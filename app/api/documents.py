import logging

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import DocumentInfo, DocumentListResponse, DeleteResponse
from app.services.vector_store_service import list_documents, delete_document_chunks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
async def get_documents():
    logger.info("Listing all documents")
    try:
        docs = list_documents()
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
async def delete_document(filename: str):
    logger.info("Deleting document: %s", filename)

    if not filename or not filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty",
        )

    try:
        chunks_deleted = delete_document_chunks(filename)
    except Exception as e:
        logger.error("Failed to delete document '%s': %s", filename, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )

    if chunks_deleted == 0:
        logger.warning("Document not found: %s", filename)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{filename}' not found",
        )

    return DeleteResponse(
        status="success",
        filename=filename,
        chunks_deleted=chunks_deleted,
    )
