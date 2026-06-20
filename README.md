# RAG Application - Phase 5

PDF Upload → Text Extraction → Chunking → Embedding → ChromaDB + BM25 → Hybrid Retrieval → Cross-Encoder Reranking → Answer Generation

## Tech Stack

- Python 3.11+
- FastAPI
- ChromaDB
- Sentence Transformers
- PyPDF
- Hugging Face Inference API (Meta Llama)
- Pydantic Settings
- BM25 (rank-bm25)
- Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2)

## Setup

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable            | Default                                        | Description                           |
| ------------------- | ---------------------------------------------- | ------------------------------------- |
| `CHROMA_PATH`       | `./chroma_db`                                   | ChromaDB storage path                 |
| `EMBEDDING_MODEL`   | `sentence-transformers/all-MiniLM-L6-v2`        | Embedding model name                  |
| `TOP_K_RESULTS`     | `5`                                             | Number of chunks to retrieve (legacy) |
| `MAX_CONTEXT_CHARS` | `3000`                                          | Max context characters sent to LLM    |
| `VECTOR_TOP_K`      | `10`                                            | Top candidates from dense vector search |
| `BM25_TOP_K`        | `10`                                            | Top candidates from BM25 sparse search |
| `RERANK_TOP_K`      | `5`                                             | Final top chunks after cross-encoder reranking |
| `HF_API_KEY`        | —                                              | **Required.** Hugging Face API token  |
| `LLM_MODEL`         | `meta-llama/Llama-3.1-8B-Instruct`             | Hugging Face model ID                 |
| `LLM_TIMEOUT`       | `60`                                            | LLM API timeout in seconds            |

### Getting a Hugging Face API Key

1. Go to https://huggingface.co/settings/tokens
2. Create a new token with read permissions
3. Add it to your `.env` file as `HF_API_KEY=`

## Run

```bash
uvicorn app.main:app --reload
```

Server starts at `http://localhost:8000`.

## RAG Flow

```
Question
    ├──→ Dense Retrieval (ChromaDB) — Top 10
    └──→ Sparse Retrieval (BM25) — Top 10
              ↓
         Merge Candidates
              ↓
         Remove Duplicates
              ↓
    Cross-Encoder Reranker — Top 5
              ↓
    Context Optimization (near-duplicate removal, truncation)
              ↓
    Context + Question → Prompt
              ↓ (Hugging Face Inference API)
    Meta Llama generates answer
              ↓
    Answer + Source Citations + Retrieval Stats
```

## API

### POST /upload

Upload a PDF file for processing. Supports multiple documents — each chunk tracks its originating filename.

**Request:** `multipart/form-data` with a `file` field.

**Response:**

```json
{
  "status": "success",
  "filename": "document.pdf",
  "chunks_created": 124,
  "embeddings_created": 124
}
```

### POST /query

Retrieve relevant chunks without answer generation.

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the document about?"}'
```

### POST /ask

Full RAG pipeline — retrieve + generate answer with source citations.

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the main topic of the document?"}'
```

**Response:**

```json
{
  "question": "What is the main topic of the document?",
  "answer": "The document discusses machine learning techniques...",
  "sources_used": 2,
  "sources": [
    {
      "filename": "document.pdf",
      "chunk_id": "5"
    },
    {
      "filename": "document.pdf",
      "chunk_id": "12"
    }
  ],
  "retrieval_stats": {
    "vector_candidates": 10,
    "bm25_candidates": 8,
    "reranked_chunks": 5
  }
}
```

### POST /ask/stream

Streaming version of `/ask`. Returns tokens incrementally as a JSON stream.

```bash
curl -X POST http://localhost:8000/ask/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"Summarize the document."}'
```

**Response format** (streamed as JSON):

```json
{
  "sources": [
    {"filename": "document.pdf", "chunk_id": "5"},
    {"filename": "document.pdf", "chunk_id": "12"}
  ],
  "retrieval_stats": {
    "vector_candidates": 10,
    "bm25_candidates": 8,
    "reranked_chunks": 5
  },
  "tokens": ["The", " document", " discusses", " ..."]
}
```

If no relevant content is found in any endpoint:

```json
{
  "question": "...",
  "answer": "I could not find the answer in the provided document.",
  "sources_used": 0,
  "sources": [],
  "retrieval_stats": {
    "vector_candidates": 10,
    "bm25_candidates": 0,
    "reranked_chunks": 0
  }
}
```

### GET /documents

List all uploaded documents with chunk counts.

```bash
curl http://localhost:8000/documents
```

**Response:**

```json
{
  "documents": [
    {
      "filename": "contract.pdf",
      "chunks": 120,
      "uploaded_at": "2026-06-19T12:00:00+00:00"
    },
    {
      "filename": "manual.pdf",
      "chunks": 250,
      "uploaded_at": "2026-06-19T12:05:00+00:00"
    }
  ],
  "total": 2
}
```

### DELETE /documents/{filename}

Delete a document and all its chunks from ChromaDB.

```bash
curl -X DELETE http://localhost:8000/documents/manual.pdf
```

**Response:**

```json
{
  "status": "success",
  "filename": "manual.pdf",
  "chunks_deleted": 250
}
```

## Features

### Hybrid Retrieval (Dense + Sparse)

Retrieval combines two complementary approaches:

- **Dense Retrieval (ChromaDB):** Semantic vector search using sentence-transformers embeddings. Captures meaning and conceptual similarity.
- **Sparse Retrieval (BM25):** Keyword-based lexical search using the `rank-bm25` library. Excels at exact term matching and rare word recall.

Both retrieval paths run in parallel. Candidates are merged, deduplicated by content, and sent to the reranker.

### Cross-Encoder Reranking

After hybrid retrieval, a **Cross-Encoder** (`cross-encoder/ms-marco-MiniLM-L-6-v2`) scores each candidate pair `(question, chunk)` and returns a relevance score. The top `RERANK_TOP_K` chunks are passed to the LLM. This significantly improves precision compared to relying on embedding similarity alone.

### Context Optimization

Before building the final prompt:

1. **Exact deduplication** — identical chunks from either retrieval path are merged
2. **Near-duplicate removal** — chunks with >80% Jaccard token overlap are filtered out
3. **Context truncation** — oversized contexts are trimmed to `MAX_CONTEXT_CHARS`

### Retrieval Performance Monitoring

Every `/ask` response includes optional `retrieval_stats` metadata:

```json
"retrieval_stats": {
  "vector_candidates": 10,
  "bm25_candidates": 8,
  "reranked_chunks": 5
}
```

The following timings are also logged server-side for each request:
- Vector search time
- BM25 search time
- Reranking time
- Total retrieval time

### Multi-Document Support

Multiple PDFs coexist in the same ChromaDB collection. Each chunk is tagged with its originating `filename`, `chunk_index`, and `uploaded_at` timestamp. Retrieval returns chunks from all documents, and the answer cites which document each chunk came from.

### Source Citations

Every `/ask` response includes a `sources` array with `filename` and `chunk_id` for each unique chunk used to generate the answer.

### Streaming Responses

`POST /ask/stream` returns tokens one at a time as a JSON array, preceded by the source citations and retrieval stats. The response uses `Transfer-Encoding: chunked` so the client can render tokens incrementally.

### Document Management

- `GET /documents` — list all uploaded documents and their chunk counts
- `DELETE /documents/{filename}` — remove a document and all its chunks

### BM25 Index Synchronization

The BM25 index is built automatically from ChromaDB on first query. It is kept synchronized:

- **On upload:** new chunks are added to ChromaDB, and the BM25 index is marked dirty (rebuilds on next query)
- **On delete:** chunks are removed from ChromaDB, and the BM25 index is marked dirty

## Project Structure

```
rag_app/
├── app/
│   ├── api/
│   │   ├── upload.py
│   │   ├── query.py
│   │   ├── ask.py
│   │   └── documents.py
│   ├── services/
│   │   ├── pdf_service.py
│   │   ├── chunking_service.py
│   │   ├── embedding_service.py
│   │   ├── vector_store_service.py
│   │   ├── bm25_service.py              # BM25 sparse retrieval
│   │   ├── hybrid_retrieval_service.py   # Dense + sparse + rerank pipeline
│   │   ├── reranker_service.py           # Cross-encoder reranking
│   │   ├── retrieval_service.py
│   │   ├── llm_service.py
│   │   └── rag_service.py
│   ├── core/
│   │   └── config.py
│   ├── models/
│   │   └── schemas.py
│   └── main.py
├── uploads/
├── chroma_db/
├── requirements.txt
├── .env.example
└── README.md
```
