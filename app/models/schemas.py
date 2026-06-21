from pydantic import BaseModel


class UploadResponse(BaseModel):
    status: str
    filename: str
    chunks_created: int
    embeddings_created: int


class QuestionRequest(BaseModel):
    question: str


class ChunkResult(BaseModel):
    chunk_id: str
    source: str
    content: str


class QueryResponse(BaseModel):
    question: str
    results_found: int
    chunks: list[ChunkResult]


AskRequest = QuestionRequest


class SourceCitation(BaseModel):
    filename: str
    chunk_id: str


class RetrievalStats(BaseModel):
    vector_candidates: int
    bm25_candidates: int
    reranked_chunks: int
    retrieval_latency_ms: float = 0.0
    rerank_latency_ms: float = 0.0
    llm_latency_ms: float | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    sources_used: int
    sources: list[SourceCitation]
    retrieval_stats: RetrievalStats | None = None


class DocumentInfo(BaseModel):
    filename: str
    chunks: int
    uploaded_at: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


class DeleteResponse(BaseModel):
    status: str
    filename: str
    chunks_deleted: int



