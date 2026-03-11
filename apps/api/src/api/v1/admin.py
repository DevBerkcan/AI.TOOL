"""Admin endpoints: stats, users, audit logs, model config."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db
from src.core.security import require_role, UserContext
from src.models.entities import (
    AuditLog, Chunk, Connector, Document, ModelConfig,
    QueryHistory, User, UserRole,
)
from src.schemas.api import (
    AuditLogResponse, DashboardStats, ModelConfigResponse,
    ModelConfigUpdate, RoleUpdateRequest, UserListItem,
)

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard statistics."""
    t = user.tenant_id
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    docs = await db.scalar(select(func.count(Document.id)).where(Document.tenant_id == t))
    chunks = await db.scalar(select(func.count(Chunk.id)).where(Chunk.tenant_id == t))
    queries = await db.scalar(
        select(func.count(QueryHistory.id)).where(
            QueryHistory.tenant_id == t, QueryHistory.created_at >= seven_days_ago
        )
    )
    users = await db.scalar(select(func.count(User.id)).where(User.tenant_id == t))
    connectors = await db.scalar(
        select(func.count(Connector.id)).where(Connector.tenant_id == t, Connector.is_active == True)
    )

    return DashboardStats(
        total_documents=docs or 0,
        total_chunks=chunks or 0,
        queries_last_7d=queries or 0,
        total_users=users or 0,
        active_connectors=connectors or 0,
    )


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all users for the tenant."""
    result = await db.scalars(
        select(User).where(User.tenant_id == user.tenant_id).order_by(User.display_name)
    )
    return [
        UserListItem(
            id=u.id, email=u.email, display_name=u.display_name,
            role=u.role.value, is_active=u.is_active, last_login=u.last_login,
        )
        for u in result.all()
    ]


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    body: RoleUpdateRequest,
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role."""
    target = await db.scalar(
        select(User).where(User.id == user_id, User.tenant_id == user.tenant_id)
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.role = UserRole(body.role)
    return {"status": "updated"}


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    action: str | None = Query(None),
):
    """List audit logs."""
    query = select(AuditLog).where(AuditLog.tenant_id == user.tenant_id)
    if action:
        query = query.where(AuditLog.action == action)
    query = query.order_by(AuditLog.created_at.desc()).limit(limit)

    result = await db.scalars(query)
    return [
        AuditLogResponse(
            id=a.id, user_id=a.user_id, action=a.action,
            resource_type=a.resource_type, resource_id=a.resource_id,
            details=a.details or {}, ip_address=a.ip_address,
            created_at=a.created_at,
        )
        for a in result.all()
    ]


@router.get("/model-config", response_model=list[ModelConfigResponse])
async def list_model_configs(
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List AI model configurations."""
    result = await db.scalars(
        select(ModelConfig).where(ModelConfig.tenant_id == user.tenant_id)
    )
    return [
        ModelConfigResponse(
            id=m.id, purpose=m.purpose.value, provider=m.provider,
            model_name=m.model_name, is_primary=m.is_primary, is_fallback=m.is_fallback,
        )
        for m in result.all()
    ]


@router.put("/model-config/{config_id}")
async def update_model_config(
    config_id: uuid.UUID,
    body: ModelConfigUpdate,
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update AI model configuration."""
    mc = await db.scalar(
        select(ModelConfig).where(
            ModelConfig.id == config_id, ModelConfig.tenant_id == user.tenant_id
        )
    )
    if not mc:
        raise HTTPException(status_code=404, detail="Config not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(mc, field, value)

    return {"status": "updated"}
