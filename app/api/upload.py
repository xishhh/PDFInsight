import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.core.config import settings
from app.models.schemas import UploadResponse
from app.services.pdf_service import save_uploaded_file, extract_text_from_pdf
from app.services.chunking_service import chunk_text
from app.services.embedding_service import generate_embeddings
from app.services.vector_store_service import store_chunks

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
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

    logger.info("Uploading file: %s (%d bytes)", file.filename, len(content))

    filename = file.filename
    file_path = None
    try:
        file_path = save_uploaded_file(UPLOAD_DIR, filename, content)
        text = extract_text_from_pdf(file_path)
        chunks = chunk_text(text)
        embeddings = generate_embeddings(chunks)
        count = store_chunks(chunks, embeddings, filename)
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

    return UploadResponse(
        status="success",
        filename=filename,
        chunks_created=len(chunks),
        embeddings_created=count,
    )
