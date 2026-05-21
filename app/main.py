import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import internal_router, public_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.database import Base, SessionLocal, engine
from app.db.database import check_database
from app.db.seed import seed_demo_data
from app.security.auth import require_internal_api_key


logger = logging.getLogger("app.request")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.auto_init_local_db and not settings.is_production and settings.database_url.startswith("sqlite"):
        _ensure_sqlite_parent(settings.database_url)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_demo_data(db)
        finally:
            db.close()
    yield


def _ensure_sqlite_parent(database_url: str) -> None:
    raw_path = database_url.replace("sqlite:///", "", 1)
    path = Path(urlparse(raw_path).path or raw_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    if settings.is_production and not settings.internal_api_key:
        raise RuntimeError("INTERNAL_API_KEY must be configured when APP_ENV=production")
    if settings.is_production and not settings.auth_tokens:
        raise RuntimeError("AUTH_TOKENS_JSON must configure at least one bearer token when APP_ENV=production")
    if settings.is_production and not settings.public_channel_token:
        raise RuntimeError("PUBLIC_CHANNEL_TOKEN must be configured when APP_ENV=production")
    if settings.is_production and settings.database_url.startswith("sqlite"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL/MySQL when APP_ENV=production")
    if settings.is_production and settings.vector_store != "milvus":
        raise RuntimeError("VECTOR_STORE must be milvus when APP_ENV=production")

    app = FastAPI(
        title="enterprise-agentops-platform",
        description="Production-oriented multi-agent service for marketing, sales, and customer QA.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.include_router(internal_router, prefix="/api")
    app.include_router(public_router, prefix="/api")
    static_dir = Path(__file__).resolve().parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/")
        def web_app():
            return FileResponse(static_dir / "index.html")

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:12]}"
        request.state.request_id = request_id
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed method=%s path=%s status=%s duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "request_id": getattr(request.state, "request_id", "unknown")},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", f"req_{uuid4().hex[:12]}")
        logger.exception(
            "unhandled_exception path=%s request_id=%s error=%s",
            request.url.path,
            request_id,
            exc.__class__.__name__,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "internal_server_error", "request_id": request_id},
        )

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/health/db", dependencies=[Depends(require_internal_api_key)])
    def health_db():
        check_database()
        return {"ok": True, "database": "reachable"}

    return app


app = create_app()
