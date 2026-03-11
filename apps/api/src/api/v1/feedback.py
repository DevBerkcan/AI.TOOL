"""Feedback endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db
from src.core.security import get_current_user, require_role, UserContext
from src.models.entities import Feedback, FeedbackRating
from src.schemas.api import FeedbackCreate, FeedbackResponse

router = APIRouter()


@router.post("", status_code=201)
async def create_feedback(
    body: FeedbackCreate,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback on an answer."""
    fb = Feedback(
        tenant_id=user.tenant_id,
        query_id=body.query_id,
        user_id=user.sub,
        rating=FeedbackRating(body.rating),
        comment=body.comment,
    )
    db.add(fb)
    return {"status": "created"}


@router.get("", response_model=list[FeedbackResponse])
async def list_feedback(
    user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    rating: str | None = Query(None),
):
    """List feedback (Admin only)."""
    query = select(Feedback).where(Feedback.tenant_id == user.tenant_id)
    if rating:
        query = query.where(Feedback.rating == rating)
    query = query.order_by(Feedback.created_at.desc()).limit(limit)

    result = await db.scalars(query)
    return [
        FeedbackResponse(
            id=f.id, query_id=f.query_id, rating=f.rating.value,
            comment=f.comment, created_at=f.created_at,
        )
        for f in result.all()
    ]
