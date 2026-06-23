import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.upload import router as upload_router
from app.api.query import router as query_router
from app.api.ask import router as ask_router
from app.api.documents import router as documents_router
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

class ChromaTelemetryFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "Failed to send telemetry event" not in record.getMessage()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for name in (
        "chromadb.telemetry.product.posthog",
        "httpx",
        "urllib3",
        "sentence_transformers",
        "chromadb",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger("chromadb.telemetry.product.posthog").addFilter(
        ChromaTelemetryFilter()
    )


configure_logging()


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.embedding_service import get_embedding_model
    from app.services.reranker_service import get_reranker
    from app.services.vector_store_service import get_chroma_collection
    from app.services.bm25_service import mark_dirty

    # -- Startup validation --
    if not settings.HF_API_KEY:
        logger.error(
            "HF_API_KEY is not set. LLM features (/ask, /ask/stream) will fail. "
            "Set it in .env or via environment variable."
        )

    # -- Storage directories --
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory ready: %s", settings.UPLOAD_DIR)

    # -- Clear Chroma on start if configured --
    if settings.CLEAR_CHROMA_ON_START:
        collection = get_chroma_collection()
        count = collection.count()
        if count:
            all_ids = collection.get()["ids"]
            collection.delete(ids=all_ids)
            logger.info("Cleared %d chunks from ChromaDB", count)
        mark_dirty()

    # -- Model warmup --
    logger.info("Loading embedding model...")
    get_embedding_model()
    logger.info("Embedding model loaded")

    logger.info("Loading reranker...")
    get_reranker()
    logger.info("Reranker loaded")

    logger.info("Connecting to vector database...")
    get_chroma_collection()
    logger.info("Vector database ready")

    logger.info("Application startup complete")
    yield
    logger.info("Application shutting down")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RAG Application",
    version="6.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_origin_regex=r"https://.*\.hf\.space",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-ID"],
)


# -- Request logging middleware --

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    logger.info(
        "%s %s -> %d (%.4fs)",
        request.method, request.url.path, response.status_code, elapsed,
    )
    return response


# -- Static files & templates --

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# -- Routes --

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "active_page": "upload"}
    )


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse(
        "chat.html", {"request": request, "active_page": "chat"}
    )


@app.get("/health")
async def health():
    return {"status": "healthy"}


app.include_router(upload_router)
app.include_router(query_router)
app.include_router(ask_router)
app.include_router(documents_router)
