from pydantic import BaseModel


class UploadResponse(BaseModel):
    status: str
    filename: str
    chunks_created: int
    embeddings_created: int


class QueryRequest(BaseModel):
    question: str


class ChunkResult(BaseModel):
    chunk_id: str
    source: str
    content: str


class QueryResponse(BaseModel):
    question: str
    results_found: int
    chunks: list[ChunkResult]


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    answer: str
    sources_used: int
