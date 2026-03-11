"""Connector management endpoints."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db
from src.core.security import get_current_user, require_role, UserContext
from src.models.entities import Connector, SourceType, SyncJob, SyncJobStatus
from src.schemas.api import (
    ConnectorCreate, ConnectorResponse, ConnectorUpdate,
    SyncJobResponse, SyncTriggerResponse,
)
from src.services.audit import audit_log

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=list[ConnectorResponse])
async def list_connectors(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all connectors for the current tenant."""
    result = await db.scalars(
        select(Connector)
        .where(Connector.tenant_id == user.tenant_id)
        .order_by(Connector.created_at.desc())
    )
    return [
        ConnectorResponse(
            id=c.id, type=c.type.value, name=c.name, is_active=c.is_active,
            last_sync_at=c.last_sync_at, sync_interval_min=c.sync_interval_min,
            created_at=c.created_at,
        )
        for c in result.all()
    ]


@router.post("", response_model=ConnectorResponse, status_code=201)
async def create_connector(
    body: ConnectorCreate,
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new connector (Admin only)."""
    try:
        source_type = SourceType(body.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid type: {body.type}")

    connector = Connector(
        tenant_id=user.tenant_id,
        type=source_type,
        name=body.name,
        config=body.config,
    )
    db.add(connector)
    await db.flush()

    await audit_log(db, user, "connector_create", "connector", str(connector.id), {"type": body.type})

    return ConnectorResponse(
        id=connector.id, type=connector.type.value, name=connector.name,
        is_active=connector.is_active, last_sync_at=None,
        sync_interval_min=connector.sync_interval_min, created_at=connector.created_at,
    )


@router.put("/{connector_id}", status_code=200)
async def update_connector(
    connector_id: uuid.UUID,
    body: ConnectorUpdate,
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update connector configuration."""
    conn = await db.scalar(
        select(Connector).where(
            Connector.id == connector_id, Connector.tenant_id == user.tenant_id
        )
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Connector not found")

    if body.name is not None:
        conn.name = body.name
    if body.config is not None:
        conn.config = body.config
    if body.is_active is not None:
        conn.is_active = body.is_active
    if body.sync_interval_min is not None:
        conn.sync_interval_min = body.sync_interval_min

    await audit_log(db, user, "connector_update", "connector", str(connector_id))
    return {"status": "updated"}


@router.delete("/{connector_id}", status_code=204)
async def delete_connector(
    connector_id: uuid.UUID,
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Delete connector and all associated documents."""
    conn = await db.scalar(
        select(Connector).where(
            Connector.id == connector_id, Connector.tenant_id == user.tenant_id
        )
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Connector not found")

    # TODO: Delete all documents and vectors for this connector
    await db.delete(conn)
    await audit_log(db, user, "connector_delete", "connector", str(connector_id))


@router.post("/{connector_id}/sync", response_model=SyncTriggerResponse)
async def trigger_sync(
    connector_id: uuid.UUID,
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a sync job."""
    conn = await db.scalar(
        select(Connector).where(
            Connector.id == connector_id, Connector.tenant_id == user.tenant_id
        )
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Connector not found")

    job = SyncJob(
        tenant_id=user.tenant_id,
        connector_id=connector_id,
        status=SyncJobStatus.pending,
    )
    db.add(job)
    await db.flush()

    # TODO: Enqueue sync worker
    # await queue.enqueue("run_connector_sync", job_id=str(job.id))

    return SyncTriggerResponse(sync_job_id=job.id, status="pending")


@router.get("/{connector_id}/syncs", response_model=list[SyncJobResponse])
async def list_sync_jobs(
    connector_id: uuid.UUID,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    """Get sync job history for a connector."""
    result = await db.scalars(
        select(SyncJob)
        .where(SyncJob.connector_id == connector_id, SyncJob.tenant_id == user.tenant_id)
        .order_by(SyncJob.created_at.desc())
        .limit(limit)
    )
    return [
        SyncJobResponse(
            id=j.id, connector_id=j.connector_id, status=j.status.value,
            started_at=j.started_at, completed_at=j.completed_at,
            documents_synced=j.documents_synced, documents_failed=j.documents_failed,
            error_message=j.error_message,
        )
        for j in result.all()
    ]
