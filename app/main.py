from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db.database import check_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="enterprise-agentops-platform",
        description="Multi-agent platform for sales, marketing, customer QA, RAG, code search, memory, audit, and tool execution.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router, prefix="/api")

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/health/db")
    def health_db():
        check_database()
        return {"ok": True, "database": "reachable"}

    return app


app = create_app()
