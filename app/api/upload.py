import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.models.schemas import UploadResponse
from app.services.pdf_service import save_uploaded_file, extract_text_from_pdf
from app.services.chunking_service import chunk_text
from app.services.embedding_service import generate_embeddings
from app.services.vector_store_service import store_chunks

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    content = await file.read()
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    await file.seek(0)

    logger.info("Uploading file: %s (%d bytes)", file.filename, len(content))

    try:
        file_path = await save_uploaded_file(UPLOAD_DIR, file)
        text = extract_text_from_pdf(file_path)
        chunks = chunk_text(text)
        embeddings = generate_embeddings(chunks)
        count = store_chunks(chunks, embeddings, file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return UploadResponse(
        status="success",
        filename=file.filename,
        chunks_created=len(chunks),
        embeddings_created=count,
    )
