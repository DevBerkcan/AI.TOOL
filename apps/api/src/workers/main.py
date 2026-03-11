"""Background worker — arq-based async task processing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import structlog
from arq.connections import RedisSettings

from src.core.config import settings

logger = structlog.get_logger()

UPLOADS_DIR = Path("/app/uploads")


# ── Job Functions ────────────────────────────────────────────────────────
async def ingest_document(ctx: dict, document_id: str):
    """Full ingestion pipeline: parse → chunk → embed → index."""
    from src.core.database import async_session
    from src.ingestion.chunker import chunk_document
    from src.ingestion.embedder import embed_and_index_chunks
    from src.ingestion.parser import parse_document
    from src.models.entities import Chunk, Document, DocumentStatus

    logger.info("Starting document ingestion", document_id=document_id)

    async with async_session() as db:
        doc = await db.get(Document, uuid.UUID(document_id))
        if not doc:
            logger.error("Document not found", document_id=document_id)
            return

        try:
            # 1. Read file bytes from local upload storage
            doc.status = DocumentStatus.parsing
            await db.commit()

            file_path = UPLOADS_DIR / doc.blob_path
            if not file_path.exists():
                raise FileNotFoundError(f"Upload not found at {file_path}")
            content = file_path.read_bytes()

            # 2. Parse document to plain text
            parsed = await parse_document(
                content=content,
                filename=doc.title or "document.pdf",
                mime_type=doc.mime_type or "application/pdf",
                source_type=doc.source_type.value,
            )

            # 3. Split into chunks
            doc.status = DocumentStatus.chunking
            await db.commit()

            chunks = chunk_document(
                document_id=str(doc.id),
                tenant_id=str(doc.tenant_id),
                title=parsed.title,
                content=parsed.content,
                source_url=doc.source_url,
                source_type=doc.source_type.value,
            )
            if not chunks:
                raise ValueError("No text could be extracted from document")

            # 4. Embed chunks and upsert into Qdrant
            doc.status = DocumentStatus.embedding
            await db.commit()

            indexed = await embed_and_index_chunks(chunks)

            # 5. Persist chunk records to PostgreSQL
            for c in chunks:
                db.add(
                    Chunk(
                        id=uuid.uuid4(),
                        tenant_id=doc.tenant_id,
                        document_id=doc.id,
                        chunk_index=c.chunk_index,
                        content=c.content,
                        token_count=c.token_count,
                        metadata=c.metadata,
                        vector_id=c.chunk_id,
                    )
                )

            doc.status = DocumentStatus.indexed
            doc.last_synced_at = datetime.now(UTC)
            await db.commit()

            logger.info(
                "Document ingestion complete",
                document_id=document_id,
                chunks=len(chunks),
                indexed=indexed,
            )

        except Exception as e:
            logger.error("Document ingestion failed", document_id=document_id, error=str(e))
            doc.status = DocumentStatus.error
            doc.error_message = str(e)
            await db.commit()
            raise


async def run_connector_sync(ctx: dict, sync_job_id: str):
    """Execute a connector sync job."""
    from src.core.database import async_session
    from src.models.entities import SyncJob, SyncJobStatus

    logger.info("Starting connector sync", sync_job_id=sync_job_id)

    async with async_session() as db:
        job = await db.get(SyncJob, uuid.UUID(sync_job_id))
        if not job:
            logger.error("SyncJob not found", sync_job_id=sync_job_id)
            return

        job.status = SyncJobStatus.running
        job.started_at = datetime.now(UTC)
        await db.commit()

        # TODO: load connector, run connector.sync(), queue ingest_document per document
        logger.info("Connector sync complete (stub)", sync_job_id=sync_job_id)

        job.status = SyncJobStatus.completed
        job.completed_at = datetime.now(UTC)
        await db.commit()


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
