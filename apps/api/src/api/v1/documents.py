"""Document endpoints: upload, list, detail, delete."""

from __future__ import annotations

import hashlib
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db
from src.core.security import get_current_user, UserContext
from src.models.entities import Chunk, Document, DocumentStatus, SourceType
from src.schemas.api import DocumentResponse, DocumentUploadResponse
from src.services.audit import audit_log

logger = structlog.get_logger()
router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF document for indexing."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")

    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicates
    existing = await db.scalar(
        select(Document).where(
            Document.tenant_id == user.tenant_id,
            Document.content_hash == content_hash,
        )
    )
    if existing:
        return DocumentUploadResponse(
            id=existing.id, status=existing.status.value, filename=file.filename
        )

    # Create document record
    doc = Document(
        tenant_id=user.tenant_id,
        source_type=SourceType.pdf_upload,
        title=file.filename,
        content_hash=content_hash,
        mime_type=file.content_type or "application/pdf",
        blob_path=f"{user.tenant_id}/uploads/{uuid.uuid4()}/{file.filename}",
        status=DocumentStatus.pending,
    )
    db.add(doc)
    await db.flush()

    # TODO: Upload to Blob Storage
    # TODO: Queue ingestion job via arq
    # await queue.enqueue("ingest_document", doc_id=str(doc.id))

    await audit_log(db, user, "document_upload", "document", str(doc.id), {"filename": file.filename})

    return DocumentUploadResponse(
        id=doc.id, status=doc.status.value, filename=file.filename
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    connector_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all documents for the current tenant."""
    query = select(Document).where(Document.tenant_id == user.tenant_id)

    if connector_id:
        query = query.where(Document.connector_id == connector_id)
    if status:
        query = query.where(Document.status == status)

    query = query.order_by(Document.created_at.desc()).limit(limit).offset(offset)
    result = await db.scalars(query)
    docs = result.all()

    # Get chunk counts
    responses = []
    for doc in docs:
        chunk_count = await db.scalar(
            select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
        )
        responses.append(
            DocumentResponse(
                id=doc.id,
                title=doc.title,
                source_type=doc.source_type.value,
                status=doc.status.value,
                source_url=doc.source_url,
                chunks_count=chunk_count or 0,
                created_at=doc.created_at,
                last_synced_at=doc.last_synced_at,
            )
        )
    return responses


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get document details."""
    doc = await db.scalar(
        select(Document).where(
            Document.id == document_id, Document.tenant_id == user.tenant_id
        )
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_count = await db.scalar(
        select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
    )
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        source_type=doc.source_type.value,
        status=doc.status.value,
        source_url=doc.source_url,
        chunks_count=chunk_count or 0,
        created_at=doc.created_at,
        last_synced_at=doc.last_synced_at,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and all its chunks/vectors."""
    doc = await db.scalar(
        select(Document).where(
            Document.id == document_id, Document.tenant_id == user.tenant_id
        )
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # TODO: Delete vectors from Qdrant
    # TODO: Delete blob from storage

    await db.delete(doc)
    await audit_log(db, user, "document_delete", "document", str(doc.id))
