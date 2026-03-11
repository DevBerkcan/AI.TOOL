"""Background worker — arq-based async task processing."""

from __future__ import annotations

import structlog
from arq import cron
from arq.connections import RedisSettings

from src.core.config import settings

logger = structlog.get_logger()


# ── Job Functions ────────────────────────────────────────────────────────
async def ingest_document(ctx: dict, document_id: str):
    """Full ingestion pipeline: parse → chunk → embed → index."""
    logger.info("Starting document ingestion", document_id=document_id)

    # 1. Load document from DB
    # 2. Fetch content from Blob Storage
    # 3. Parse document
    # 4. Chunk document
    # 5. Embed chunks
    # 6. Update document status

    # TODO: Implement full pipeline integration
    # from src.ingestion.parser import parse_document
    # from src.ingestion.chunker import chunk_document
    # from src.ingestion.embedder import embed_and_index_chunks

    logger.info("Document ingestion complete", document_id=document_id)


async def run_connector_sync(ctx: dict, sync_job_id: str):
    """Execute a connector sync job."""
    logger.info("Starting connector sync", sync_job_id=sync_job_id)

    # 1. Load sync job from DB
    # 2. Load connector config
    # 3. Run connector.sync()
    # 4. For each document: queue ingest_document
    # 5. Update sync job status

    logger.info("Connector sync complete", sync_job_id=sync_job_id)


async def refresh_permissions(ctx: dict, tenant_id: str):
    """Refresh document permissions from source systems."""
    logger.info("Refreshing permissions", tenant_id=tenant_id)
    # TODO: Implement permission refresh logic


async def reindex_documents(ctx: dict, tenant_id: str):
    """Re-embed and re-index all documents for a tenant."""
    logger.info("Starting reindex", tenant_id=tenant_id)
    # TODO: Implement reindex logic


# ── Startup / Shutdown ───────────────────────────────────────────────────
async def startup(ctx: dict):
    """Worker startup — initialize DB connection, etc."""
    logger.info("Worker starting up")


async def shutdown(ctx: dict):
    """Worker shutdown — cleanup."""
    logger.info("Worker shutting down")


# ── arq Worker Settings ─────────────────────────────────────────────────
class WorkerSettings:
    """arq worker configuration."""

    functions = [
        ingest_document,
        run_connector_sync,
        refresh_permissions,
        reindex_documents,
    ]

    cron_jobs = [
        # Scheduled connector syncs (check every 5 minutes)
        # cron(scheduled_sync_check, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    max_jobs = 10
    job_timeout = 600  # 10 minutes
    max_tries = 3
    health_check_interval = 30
