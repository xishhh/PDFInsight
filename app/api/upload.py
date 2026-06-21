import logging
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, Response, status

from app.core.config import settings
from app.models.schemas import UploadResponse
from app.services.pdf_service import save_uploaded_file, extract_text_from_pdf
from app.services.chunking_service import chunk_text
from app.services.embedding_service import generate_embeddings
from app.services.rate_limiter import check_upload_rate
from app.services.session_service import get_session_id
from app.services.vector_store_service import store_chunks, get_chroma_collection

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(settings.UPLOAD_DIR)

router = APIRouter()


def _count_session_documents(session_id: str) -> int:
    collection = get_chroma_collection()
    all_data = collection.get(include=["metadatas"], where={"session_id": session_id})
    metadatas = all_data.get("metadatas", []) or []
    seen_filenames: set[str] = set()
    for meta in metadatas:
        fname = meta.get("filename", "")
        if fname:
            seen_filenames.add(fname)
    return len(seen_filenames)


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    session_id: str = Depends(get_session_id),
):
    check_upload_rate(request, settings.UPLOAD_RATE_LIMIT)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB",
        )

    current_count = _count_session_documents(session_id)
    if current_count >= settings.MAX_DOCUMENTS_PER_SESSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {settings.MAX_DOCUMENTS_PER_SESSION} documents per session reached",
        )

    logger.info(
        "Uploading file: %s (%d bytes, session=%s)",
        file.filename, len(content), session_id,
    )

    filename = file.filename
    file_path = None
    try:
        file_path = save_uploaded_file(UPLOAD_DIR, filename, content)
        text = extract_text_from_pdf(file_path)
        chunks = chunk_text(text)
        embeddings = generate_embeddings(chunks)
        count = store_chunks(chunks, embeddings, filename, session_id=session_id)
    except ValueError as e:
        if file_path and file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        if file_path and file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process file",
        )

    logger.info(
        "Upload successful: %s (%d chunks, session=%s)",
        filename, len(chunks), session_id,
    )
    return UploadResponse(
        status="success",
        filename=filename,
        chunks_created=len(chunks),
        embeddings_created=count,
    )
