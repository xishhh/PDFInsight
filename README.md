# RAG Application - Phase 3

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

| Variable          | Default                                        | Description                     |
| ----------------- | ---------------------------------------------- | ------------------------------- |
| `CHROMA_PATH`     | `./chroma_db`                                   | ChromaDB storage path           |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2`        | Embedding model name            |
| `TOP_K_RESULTS`   | `3`                                             | Number of chunks to retrieve    |
| `HF_API_KEY`      | —                                              | **Required.** Hugging Face API token |
| `LLM_MODEL`       | `meta-llama/Llama-3.1-8B-Instruct`             | Hugging Face model ID           |
| `LLM_TIMEOUT`     | `60`                                            | LLM API timeout in seconds      |

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
    ↓ (build context)
Context + Question → Prompt
    ↓ (Hugging Face Inference API)
Meta Llama generates answer
```

## API

### POST /upload

Upload a PDF file for processing.

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

Full RAG pipeline — retrieve + generate answer.

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
  "sources_used": 3
}
```

If no relevant content is found:

```json
{
  "question": "...",
  "answer": "I could not find the answer in the provided document.",
  "sources_used": 0
}
```
## Project Structure

```
rag_app/
├── app/
│   ├── api/
│   │   ├── upload.py
│   │   ├── query.py
│   │   └── ask.py
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
