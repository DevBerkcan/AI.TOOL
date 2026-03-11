"""Chat endpoints: query with streaming, conversation history."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from src.core.dependencies import get_db
from src.core.security import UserContext, get_current_user
from src.models.entities import QueryHistory
from src.rag.pipeline import RAGPipeline
from src.schemas.api import (
    ChatRequest,
    ConversationListItem,
)

logger = structlog.get_logger()
router = APIRouter()


@router.post("")
async def chat(
    request: ChatRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ask a question. Returns SSE stream with tokens and sources."""
    conversation_id = request.conversation_id or uuid.uuid4()

    pipeline = RAGPipeline(db=db, tenant_id=user.tenant_id, user_id=user.sub)

    async def event_generator():
        try:
            async for event in pipeline.run(
                query=request.query,
                conversation_id=conversation_id,
            ):
                yield event
        except Exception as e:
            logger.error("Chat pipeline error", error=str(e))
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List user's conversations."""
    # Get distinct conversation IDs with first message as title
    subq = (
        select(
            QueryHistory.conversation_id,
            func.min(QueryHistory.query_text).label("title"),
            func.count(QueryHistory.id).label("message_count"),
            func.min(QueryHistory.created_at).label("created_at"),
            func.max(QueryHistory.created_at).label("updated_at"),
        )
        .where(QueryHistory.tenant_id == user.tenant_id)
        .where(QueryHistory.user_id == user.sub)
        .group_by(QueryHistory.conversation_id)
        .order_by(func.max(QueryHistory.created_at).desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(subq)
    rows = result.all()

    return [
        ConversationListItem(
            id=row.conversation_id,
            title=row.title[:80] if row.title else "Untitled",
            message_count=row.message_count,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full conversation messages."""
    result = await db.scalars(
        select(QueryHistory)
        .where(
            QueryHistory.tenant_id == user.tenant_id,
            QueryHistory.conversation_id == conversation_id,
        )
        .order_by(QueryHistory.created_at)
    )
    messages = result.all()
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "id": conversation_id,
        "messages": [
            {
                "role": "user",
                "content": m.query_text,
                "sources": [],
                "created_at": m.created_at,
            }
            if i % 2 == 0
            else {
                "role": "assistant",
                "content": m.answer_text or "",
                "sources": m.sources or [],
                "model_used": m.model_used,
                "created_at": m.created_at,
            }
            for i, m in enumerate(messages)
        ],
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    from sqlalchemy import delete

    await db.execute(
        delete(QueryHistory).where(
            QueryHistory.tenant_id == user.tenant_id,
            QueryHistory.conversation_id == conversation_id,
        )
    )
