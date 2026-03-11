"""Pydantic schemas for API request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Auth ─────────────────────────────────────────────────────────────────
class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    tenant_id: uuid.UUID


# ── Chat ─────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[uuid.UUID] = None


class SourceReference(BaseModel):
    document_id: uuid.UUID
    title: str
    source_url: Optional[str] = None
    snippet: str
    score: float


class ChatMessageResponse(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    sources: list[SourceReference] = []
    model_used: Optional[str] = None
    created_at: datetime


class ConversationListItem(BaseModel):
    id: uuid.UUID
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    id: uuid.UUID
    messages: list[ChatMessageResponse]


# ── Documents ────────────────────────────────────────────────────────────
class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    source_type: str
    status: str
    source_url: Optional[str] = None
    chunks_count: int = 0
    created_at: datetime
    last_synced_at: Optional[datetime] = None


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    status: str
    filename: str


# ── Connectors ───────────────────────────────────────────────────────────
class ConnectorCreate(BaseModel):
    type: str  # sharepoint | confluence | pdf_upload
    name: str = Field(..., min_length=1, max_length=255)
    config: dict[str, Any] = {}


class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    sync_interval_min: Optional[int] = None


class ConnectorResponse(BaseModel):
    id: uuid.UUID
    type: str
    name: str
    is_active: bool
    last_sync_at: Optional[datetime] = None
    sync_interval_min: int
    created_at: datetime


class SyncJobResponse(BaseModel):
    id: uuid.UUID
    connector_id: uuid.UUID
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    documents_synced: int
    documents_failed: int
    error_message: Optional[str] = None


class SyncTriggerResponse(BaseModel):
    sync_job_id: uuid.UUID
    status: str = "pending"


# ── Feedback ─────────────────────────────────────────────────────────────
class FeedbackCreate(BaseModel):
    query_id: uuid.UUID
    rating: str  # positive | negative
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    query_id: uuid.UUID
    rating: str
    comment: Optional[str] = None
    created_at: datetime


# ── Admin ────────────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_documents: int
    total_chunks: int
    queries_last_7d: int
    total_users: int
    active_connectors: int


class UserListItem(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login: Optional[datetime] = None


class RoleUpdateRequest(BaseModel):
    role: str


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: dict = {}
    ip_address: Optional[str] = None
    created_at: datetime


class ModelConfigResponse(BaseModel):
    id: uuid.UUID
    purpose: str
    provider: str
    model_name: str
    is_primary: bool
    is_fallback: bool


class ModelConfigUpdate(BaseModel):
    provider: Optional[str] = None
    model_name: Optional[str] = None
    config: Optional[dict] = None
    is_primary: Optional[bool] = None
    is_fallback: Optional[bool] = None


# ── Generic ──────────────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int
