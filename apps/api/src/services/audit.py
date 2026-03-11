"""Audit logging service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import UserContext
from src.models.entities import AuditLog


async def audit_log(
    db: AsyncSession,
    user: UserContext,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
):
    """Write an immutable audit log entry."""
    entry = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.sub,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(entry)
