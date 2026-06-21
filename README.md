# RAG Application

PDF Upload → Text Extraction → Chunking → Embedding → ChromaDB + BM25 → Hybrid Retrieval → Cross-Encoder Reranking → Answer Generation

## Tech Stack

- Python 3.11+
- FastAPI
- ChromaDB (persistent, file-based — no external database required)
- Sentence Transformers
- PyPDF
- Hugging Face Inference API (Meta Llama)
- Pydantic Settings
- BM25 (rank-bm25)
- Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2)

## Setup

### Local

```bash
pip install -r requirements.txt
```

Copy the environment file and add your Hugging Face API key:

```bash
cp .env.example .env
# Edit .env and set HF_API_KEY=
```

### Docker

```bash
docker compose up --build
```

The first startup will download embedding and reranker models (~500 MB total). Subsequent starts use the cached models.

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable                  | Default                                        | Required | Description                              |
| ------------------------- | ---------------------------------------------- | -------- | ---------------------------------------- |
| `HF_API_KEY`              | —                                              | Yes      | Hugging Face API token (get one at https://huggingface.co/settings/tokens) |
| `LLM_MODEL`               | `meta-llama/Llama-3.1-8B-Instruct`             | No       | Hugging Face model ID for inference      |
| `CHROMA_PATH`             | `{project}/chroma_db`                          | No       | ChromaDB persistent storage path         |
| `UPLOAD_DIR`              | `{project}/uploads`                            | No       | PDF upload directory                     |
| `MAX_FILE_SIZE_MB`        | `20`                                           | No       | Maximum PDF upload size in MB            |
| `VECTOR_TOP_K`            | `10`                                           | No       | Top candidates from dense vector search  |
| `BM25_TOP_K`              | `10`                                           | No       | Top candidates from BM25 sparse search   |
| `RERANK_TOP_K`            | `5`                                            | No       | Final top chunks after cross-encoder reranking |
| `ALLOWED_ORIGINS`         | `http://localhost:8000`                        | No       | Comma-separated CORS origins             |

### Getting a Hugging Face API Key

1. Go to https://huggingface.co/settings/tokens
2. Create a new token with read permissions
3. Add it to your `.env` file as `HF_API_KEY=`

## Run

### Local

```bash
uvicorn app.main:app --reload
```

### Docker

```bash
docker compose up --build
```

Server starts at `http://localhost:8000`.

## Deployment

This application is designed for free-tier hosting. No paid cloud services, external databases, or authentication services are required.

### Recommended: Hugging Face Spaces (Free)

[Hugging Face Spaces](https://huggingface.co/spaces) offers the best free-tier fit — 16GB RAM, 2 vCPU, and Docker support, plus you're already using HF for the LLM API.

#### One-click deploy

[![Deploy to HF Spaces](https://huggingface.co/datasets/huggingface/badges/resolve/main/deploy-to-spaces-lg.svg)](https://huggingface.co/login?return_to=%2Fnew-space%3Ftemplate%3Dstatic%26sdk%3Ddocker%26name%3Dbasic-rag)

Or create manually:

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Set **Space Name** (e.g. `basic-rag`)
3. Set **SDK** → **Docker**
4. Set **Space Hardware** → **CPU basic** (free)
5. Connect your GitHub repo (or upload the `rag_app/` folder)
6. In **Settings → Repository Secrets**, add:
   - `HF_API_KEY` — your HF token
   - `ALLOWED_ORIGINS` — `https://<your-space>.hf.space`
   - `CLEAR_CHROMA_ON_START` → `0`
7. The Space will build and start. First boot downloads ~500MB of models (~2–5 min).

> **Storage:** HF Spaces free tier disk is *ephemeral* — data is lost on restart. To persist ChromaDB and uploads across restarts, attach a [Storage Bucket](https://huggingface.co/docs/hub/en/spaces-storage) (free tier includes quota) mounted at `/data`, then set:
> - `CHROMA_PATH=/data/chroma_db`
> - `UPLOAD_DIR=/data/uploads`

### Other Options

| Platform | Notes |
|----------|-------|
| **Render** | Free tier (512MB RAM, spins down after 15min). **No persistent disk** on free tier — models re-download on every restart. Suitable only for evaluation. |
| **Railway** | No free tier — $5/month minimum (Hobby plan). Includes 5GB persistent volume. |
| **Oracle Cloud** (Always Free) | 4 ARM cores, 24GB RAM, 200GB persistent disk. Most powerful free option, but requires manual Docker setup on a VM. |

### Storage Behavior

| Path | Content | Persistence |
|------|---------|-------------|
| `chroma_db/` | ChromaDB vector database | Lost on restart without persistent disk |
| `uploads/` | Uploaded PDF files | Lost on restart without persistent disk |
| `~/.cache/huggingface/` | Downloaded embedding + reranker models (~500MB) | Lost on restart without persistent disk or Docker volume |

On platforms with ephemeral storage (HF Spaces free tier, Render free tier), all data is lost on restart. Use persistent volumes or Storage Buckets for production use.

### Environment Variables in Production

Set these as environment variables / secrets on your hosting platform (not in `.env`):

| Variable              | Required | Description |
|----------------------|----------|-------------|
| `HF_API_KEY`         | Yes      | Hugging Face API token |
| `ALLOWED_ORIGINS`    | Yes      | Your deployment domain(s) for CORS |
| `CLEAR_CHROMA_ON_START` | No   | Set to `0` in production |

### Notes

- Models download on first startup — expect ~500 MB and 2–5 minutes
- HF Inference API is free-tier friendly but has rate limits
- Session isolation uses cookies — ensure your domain uses a consistent hostname so sessions persist
- The health endpoint (`GET /health`) is available for platform uptime monitoring

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

---

## Phase 6 — Security & Session Isolation

### Session-Based Document Isolation

Every visitor receives a unique `session_id` stored in a secure HTTP-only cookie. All uploaded documents and their chunks are tagged with this `session_id`. Retrieval, listing, and deletion operations are scoped to the current session — users can never access another session's documents.

- `session_id` is auto-generated as a UUID v4 on first visit
- Stored in `session_id` cookie (HTTP-only, SameSite=Lax, 1-year expiry)
- All ChromaDB metadata includes `session_id`
- Vector search uses ChromaDB's `where` filter on `session_id`
- BM25 filters results by `session_id` after scoring

### Upload Limits

- **MAX_FILE_SIZE_MB** — rejects files larger than this limit with HTTP 413
- **MAX_DOCUMENTS_PER_SESSION** — prevents unlimited storage abuse

### Rate Limiting

IP-based sliding window rate limiting protects:

| Endpoint              | Default Limit      | HTTP Code |
| --------------------- | ------------------ | --------- |
| `POST /upload`        | 5 per minute       | 429       |
| `POST /ask`           | 20 per minute      | 429       |
| `POST /ask/stream`    | 20 per minute      | 429       |

Rate limit violations are logged server-side.

### CORS Security

`ALLOWED_ORIGINS` is loaded from the environment (comma-separated). The default `*` has been removed. Configure it for your deployment domain.

### Health Check

`GET /health` returns `{"status": "healthy"}`. Used by deployment platforms (Railway, Render, etc.) for uptime monitoring.

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
│   │   ├── rag_service.py
│   │   ├── session_service.py            # Session ID management
│   │   └── rate_limiter.py               # IP-based rate limiting
│   ├── core/
│   │   └── config.py
│   ├── models/
│   │   └── schemas.py
│   └── main.py
├── uploads/
├── chroma_db/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── .env.example
└── README.md
```
