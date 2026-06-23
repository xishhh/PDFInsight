---
title: PDFInsight
emoji: 🦀
colorFrom: gray
colorTo: gray
sdk: docker
pinned: false
---

# PDFInsight — RAG-Powered Document Q&A

Upload PDFs and ask natural-language questions. The system retrieves relevant chunks using a hybrid dense + sparse search pipeline, re-ranks them with a cross-encoder, and generates answers via Llama 3.1 (8B) through the Hugging Face Inference API.

## Features

- **PDF Upload** — Drag-and-drop upload with validation (magic bytes, size, extension).
- **Hybrid Retrieval** — Dense vector search (ChromaDB + all-MiniLM-L6-v2) combined with BM25 keyword search, merged and re-ranked by a cross-encoder.
- **LLM Answering** — Context-grounded answers with source citations and retrieval latency stats. Supports streaming via SSE.
- **Session Isolation** — Cookie-based sessions keep documents separate between users.
- **Rate Limiting** — Per-IP limits for uploads (5/min) and questions (20/min).
- **Web UI** — Two-page interface (Upload + Chat) styled with Tailwind CSS.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Vector DB | ChromaDB |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Re-ranker | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| LLM | meta-llama/Llama-3.1-8B-Instruct (HF Inference API) |
| Keyword Search | rank-bm25 (BM25Okapi) |
| PDF Parsing | PyPDF2 |
| Text Splitting | langchain-text-splitters |
| Frontend | Jinja2 + Tailwind CSS (CDN) + vanilla JS |
| Deployment | Docker / Hugging Face Spaces |

## Quick Start

### Prerequisites

- Python 3.12+
- A [Hugging Face API token](https://huggingface.co/settings/tokens)

### Local (no Docker)

```bash
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set your `HF_API_KEY`:

```env
HF_API_KEY=hf_your_token_here
```

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000).

### Docker

```bash
docker compose up --build
```

## Configuration

Key environment variables (see `.env.example` for all):

| Variable | Default | Description |
|---|---|---|
| `HF_API_KEY` | — | Hugging Face API token (required) |
| `LLM_MODEL` | `meta-llama/Llama-3.1-8B-Instruct` | HF Inference API model |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `VECTOR_TOP_K` | `10` | Candidates from dense search |
| `BM25_TOP_K` | `10` | Candidates from BM25 search |
| `RERANK_TOP_K` | `5` | Final top-k after re-ranking |
| `MAX_CONTEXT_CHARS` | `3000` | Max characters for LLM context |

## Project Structure

```
rag_app/
  app/
    main.py                    # FastAPI app, lifespan, routing
    core/config.py             # Pydantic settings
    models/schemas.py          # Request/response models
    api/                       # Route handlers
    services/                  # Business logic
    templates/                 # Jinja2 pages
    static/                    # CSS & JS
  chroma_db/                   # Persistent vector store
  uploads/                     # PDF storage
  docker-compose.yml
  Dockerfile
  requirements.txt
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/upload` | Upload a PDF |
| POST | `/query` | Retrieve relevant chunks (no LLM) |
| POST | `/ask` | Ask a question (LLM answer) |
| POST | `/ask/stream` | Ask with streaming response |
| GET | `/documents` | List uploaded documents |
| DELETE | `/documents/{filename}` | Delete a document |
| GET | `/` | Upload page |
| GET | `/chat` | Chat page |
