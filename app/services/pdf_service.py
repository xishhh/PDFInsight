import logging
from pathlib import Path
from fastapi import UploadFile

from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


async def save_uploaded_file(upload_dir: Path, file: UploadFile) -> Path:
    file_path = upload_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    logger.info("Saved uploaded file: %s (%d bytes)", file.filename, len(content))
    return file_path


def extract_text_from_pdf(file_path: Path) -> str:
    logger.info("Extracting text from: %s", file_path)
    try:
        reader = PdfReader(str(file_path))
    except Exception as e:
        logger.error("Failed to read PDF '%s': %s", file_path.name, e)
        raise ValueError(f"Corrupted or invalid PDF: {file_path.name}") from e

    pages = reader.pages
    if not pages:
        logger.warning("PDF has no pages: %s", file_path.name)
        raise ValueError(f"PDF is empty: {file_path.name}")

    text_parts: list[str] = []
    for page in pages:
        page_text = page.extract_text() or ""
        text_parts.append(page_text)

    full_text = "\n".join(text_parts).strip()

    if not full_text:
        logger.warning("No extractable text in PDF: %s", file_path.name)
        raise ValueError(f"No extractable text in PDF: {file_path.name}")

    logger.info(
        "Extraction successful: %s (%d characters)", file_path.name, len(full_text)
    )
    return full_text
