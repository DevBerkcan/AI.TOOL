"""Enterprise Knowledge Copilot API."""

from contextlib import asynccontextmanager

import structlog
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import auth, chat, connectors, documents, feedback, admin
from src.core.config import settings
from src.core.database import engine, Base
from src.core.middleware import TenantMiddleware, RequestLoggingMiddleware

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting Knowledge Copilot API", environment=settings.ENVIRONMENT)
    # Create tables if they don't exist (dev only — use alembic in prod)
    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    # Shared arq job queue pool
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    yield
    logger.info("Shutting down Knowledge Copilot API")
    await app.state.arq_pool.aclose()
    await engine.dispose()


app = FastAPI(
    title="Knowledge Copilot API",
    description="Enterprise AI Knowledge Search & Automation Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ── Middleware (order matters: last added = first executed) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TenantMiddleware)

# ── Routers ──
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(connectors.router, prefix="/api/v1/connectors", tags=["Connectors"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "knowledge-copilot-api", "version": "0.1.0"}
