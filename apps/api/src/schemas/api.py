"""Pydantic schemas for API request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

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
    conversation_id: uuid.UUID | None = None


class SourceReference(BaseModel):
    document_id: uuid.UUID
    title: str
    source_url: str | None = None
    snippet: str
    score: float


class ChatMessageResponse(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    sources: list[SourceReference] = []
    model_used: str | None = None
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
    source_url: str | None = None
    chunks_count: int = 0
    created_at: datetime
    last_synced_at: datetime | None = None


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
    name: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None
    sync_interval_min: int | None = None


class ConnectorResponse(BaseModel):
    id: uuid.UUID
    type: str
    name: str
    is_active: bool
    last_sync_at: datetime | None = None
    sync_interval_min: int
    created_at: datetime


class SyncJobResponse(BaseModel):
    id: uuid.UUID
    connector_id: uuid.UUID
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    documents_synced: int
    documents_failed: int
    error_message: str | None = None


class SyncTriggerResponse(BaseModel):
    sync_job_id: uuid.UUID
    status: str = "pending"


# ── Feedback ─────────────────────────────────────────────────────────────
class FeedbackCreate(BaseModel):
    query_id: uuid.UUID
    rating: str  # positive | negative
    comment: str | None = None


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    query_id: uuid.UUID
    rating: str
    comment: str | None = None
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
    last_login: datetime | None = None


class RoleUpdateRequest(BaseModel):
    role: str


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict = {}
    ip_address: str | None = None
    created_at: datetime


class ModelConfigResponse(BaseModel):
    id: uuid.UUID
    purpose: str
    provider: str
    model_name: str
    is_primary: bool
    is_fallback: bool


class ModelConfigUpdate(BaseModel):
    provider: str | None = None
    model_name: str | None = None
    config: dict | None = None
    is_primary: bool | None = None
    is_fallback: bool | None = None


# ── Generic ──────────────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int
