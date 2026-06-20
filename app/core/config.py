from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CHROMA_PATH: str = "./chroma_db"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    TOP_K_RESULTS: int = 5
    MAX_CONTEXT_CHARS: int = 3000
    HF_API_KEY: str = ""
    LLM_MODEL: str = "meta-llama/Llama-3.1-8B-Instruct"
    LLM_TIMEOUT: int = 60
    UPLOAD_DIR: str = "./uploads"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
