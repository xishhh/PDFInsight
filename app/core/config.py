from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    CHROMA_PATH: str = str(BASE_DIR / "chroma_db")
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    MAX_CONTEXT_CHARS: int = 3000
    HF_API_KEY: str = ""
    LLM_MODEL: str = "meta-llama/Llama-3.1-8B-Instruct"
    LLM_TIMEOUT: int = 30
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    VECTOR_TOP_K: int = 10
    BM25_TOP_K: int = 10
    RERANK_TOP_K: int = 5
    CLEAR_CHROMA_ON_START: bool = False

    MAX_FILE_SIZE_MB: int = 20
    MAX_DOCUMENTS_PER_SESSION: int = 5
    UPLOAD_RATE_LIMIT: int = 5
    QUESTION_RATE_LIMIT: int = 20
    ALLOWED_ORIGINS: str = "http://localhost:8000"

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
