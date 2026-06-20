# RAG Application - Phase 4

PDF Upload → Text Extraction → Chunking → Embedding → ChromaDB → Semantic Retrieval → Answer Generation

## Tech Stack

- Python 3.11+
- FastAPI
- ChromaDB
- Sentence Transformers
- PyPDF
- Hugging Face Inference API (Meta Llama)
- Pydantic Settings

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
| `TOP_K_RESULTS`     | `5`                                             | Number of chunks to retrieve          |
| `MAX_CONTEXT_CHARS` | `3000`                                          | Max context characters sent to LLM    |
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
    ↓ (embedding)
Retrieve Top Chunks from ChromaDB
    ↓ (deduplicate, build context, truncate if needed)
Context + Question → Prompt
    ↓ (Hugging Face Inference API)
Meta Llama generates answer
    ↓
Answer + Source Citations
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
  ]
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
  "tokens": ["The", " document", " discusses", " ..."]
}
```

If no relevant content is found in any endpoint:

```json
{
  "question": "...",
  "answer": "I could not find the answer in the provided document.",
  "sources_used": 0,
  "sources": []
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

### Multi-Document Support

Multiple PDFs coexist in the same ChromaDB collection. Each chunk is tagged with its originating `filename`, `chunk_index`, and `uploaded_at` timestamp. Retrieval returns chunks from all documents, and the answer cites which document each chunk came from.

### Source Citations

Every `/ask` response includes a `sources` array with `filename` and `chunk_id` for each unique chunk used to generate the answer.

### Streaming Responses

`POST /ask/stream` returns tokens one at a time as a JSON array, preceded by the source citations. The response uses `Transfer-Encoding: chunked` so the client can render tokens incrementally.

### Document Management

- `GET /documents` — list all uploaded documents and their chunk counts
- `DELETE /documents/{filename}` — remove a document and all its chunks

### Retrieval Improvements

- **Deduplication:** identical chunk content is skipped during retrieval
- **Configurable:** `TOP_K_RESULTS` and `MAX_CONTEXT_CHARS` via environment variables
- **Context truncation:** oversized contexts are trimmed before being sent to the LLM

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
