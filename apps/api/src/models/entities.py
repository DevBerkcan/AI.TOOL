"""SQLAlchemy ORM models for all MVP tables."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer,
    String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.core.database import Base


# ── Enums ────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"


class SourceType(str, enum.Enum):
    sharepoint = "sharepoint"
    confluence = "confluence"
    pdf_upload = "pdf_upload"


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    parsing = "parsing"
    chunking = "chunking"
    embedding = "embedding"
    indexed = "indexed"
    error = "error"


class SyncJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class FeedbackRating(str, enum.Enum):
    positive = "positive"
    negative = "negative"


class ModelPurpose(str, enum.Enum):
    chat = "chat"
    embedding = "embedding"
    reranking = "reranking"


# ── Mixin ────────────────────────────────────────────────────────────────
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ── Tenant ───────────────────────────────────────────────────────────────
class Tenant(Base, TimestampMixin):
    __tablename__ = "tenant"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    entra_tenant_id = Column(String(255), unique=True, nullable=False)
    settings = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    connectors = relationship("Connector", back_populates="tenant", cascade="all, delete-orphan")


# ── User ─────────────────────────────────────────────────────────────────
class User(Base, TimestampMixin):
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    entra_object_id = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.viewer, nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))

    tenant = relationship("Tenant", back_populates="users")

    __table_args__ = (
        Index("ix_user_tenant_email", "tenant_id", "email", unique=True),
        Index("ix_user_entra", "entra_object_id"),
    )


# ── Group Mapping ────────────────────────────────────────────────────────
class GroupMapping(Base, TimestampMixin):
    __tablename__ = "group_mapping"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    entra_group_id = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    description = Column(String(255))

    __table_args__ = (
        Index("ix_gm_tenant_group", "tenant_id", "entra_group_id", unique=True),
    )


# ── Document ─────────────────────────────────────────────────────────────
class Document(Base, TimestampMixin):
    __tablename__ = "document"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    connector_id = Column(UUID(as_uuid=True), ForeignKey("connector.id", ondelete="SET NULL"), nullable=True)
    source_type = Column(Enum(SourceType), nullable=False)
    external_id = Column(String(512))
    title = Column(String(512), nullable=False)
    source_url = Column(Text)
    content_hash = Column(String(64))
    mime_type = Column(String(100))
    blob_path = Column(String(512))
    status = Column(Enum(DocumentStatus), default=DocumentStatus.pending, nullable=False)
    error_message = Column(Text)
    metadata_ = Column("metadata", JSONB, default=dict)
    last_synced_at = Column(DateTime(timezone=True))

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_doc_tenant_status", "tenant_id", "status"),
        Index("ix_doc_tenant_source", "tenant_id", "source_type"),
        Index("ix_doc_hash", "tenant_id", "content_hash"),
    )


# ── Chunk ────────────────────────────────────────────────────────────────
class Chunk(Base, TimestampMixin):
    __tablename__ = "chunk"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("document.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer)
    metadata_ = Column("metadata", JSONB, default=dict)
    vector_id = Column(String(255))

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunk_tenant", "tenant_id"),
        Index("ix_chunk_document", "document_id"),
    )


# ── Connector ────────────────────────────────────────────────────────────
class Connector(Base, TimestampMixin):
    __tablename__ = "connector"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(SourceType), nullable=False)
    name = Column(String(255), nullable=False)
    config = Column(JSONB, default=dict)  # encrypted in practice
    is_active = Column(Boolean, default=True)
    sync_interval_min = Column(Integer, default=60)
    last_sync_at = Column(DateTime(timezone=True))

    tenant = relationship("Tenant", back_populates="connectors")
    sync_jobs = relationship("SyncJob", back_populates="connector", cascade="all, delete-orphan")


# ── Sync Job ─────────────────────────────────────────────────────────────
class SyncJob(Base, TimestampMixin):
    __tablename__ = "sync_job"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    connector_id = Column(UUID(as_uuid=True), ForeignKey("connector.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(SyncJobStatus), default=SyncJobStatus.pending, nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    documents_synced = Column(Integer, default=0)
    documents_failed = Column(Integer, default=0)
    error_message = Column(Text)

    connector = relationship("Connector", back_populates="sync_jobs")


# ── Query History ────────────────────────────────────────────────────────
class QueryHistory(Base, TimestampMixin):
    __tablename__ = "query_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    query_text = Column(Text, nullable=False)
    rewritten_query = Column(Text)
    answer_text = Column(Text)
    sources = Column(JSONB, default=list)
    model_used = Column(String(100))
    provider_used = Column(String(50))
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)

    feedbacks = relationship("Feedback", back_populates="query", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_qh_tenant_user", "tenant_id", "user_id"),
        Index("ix_qh_conversation", "conversation_id"),
    )


# ── Feedback ─────────────────────────────────────────────────────────────
class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    query_id = Column(UUID(as_uuid=True), ForeignKey("query_history.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    rating = Column(Enum(FeedbackRating), nullable=False)
    comment = Column(Text)

    query = relationship("QueryHistory", back_populates="feedbacks")


# ── Audit Log ────────────────────────────────────────────────────────────
class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(255))
    details = Column(JSONB, default=dict)
    ip_address = Column(String(45))

    __table_args__ = (
        Index("ix_audit_tenant_action", "tenant_id", "action"),
        Index("ix_audit_created", "created_at"),
    )


# ── Model Config ─────────────────────────────────────────────────────────
class ModelConfig(Base, TimestampMixin):
    __tablename__ = "model_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    purpose = Column(Enum(ModelPurpose), nullable=False)
    provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    config = Column(JSONB, default=dict)
    is_primary = Column(Boolean, default=False)
    is_fallback = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_mc_tenant_purpose", "tenant_id", "purpose"),
    )
