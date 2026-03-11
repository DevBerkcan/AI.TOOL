"""Chunking service — splits documents into embedding-optimized chunks."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class ChunkResult:
    """A single chunk with metadata."""
    chunk_id: str
    content: str
    chunk_index: int
    token_count: int
    metadata: dict


def chunk_document(
    document_id: str,
    tenant_id: str,
    title: str,
    content: str,
    source_url: str | None = None,
    source_type: str = "pdf_upload",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[ChunkResult]:
    """Split document content into overlapping chunks.

    Uses recursive character splitting with heading-aware boundaries.
    """
    if not content.strip():
        return []

    # Split by paragraph boundaries first, then by sentence, then by character
    separators = ["\n\n", "\n", ". ", " ", ""]
    raw_chunks = _recursive_split(content, separators, chunk_size * 4, chunk_overlap * 4)

    results = []
    for i, chunk_text in enumerate(raw_chunks):
        if not chunk_text.strip():
            continue

        # Deterministic chunk ID
        chunk_hash = hashlib.sha256(f"{document_id}:{i}:{chunk_text[:100]}".encode()).hexdigest()[:16]
        chunk_id = f"{document_id}_{chunk_hash}"

        # Rough token count (1 token ≈ 4 chars for English/German)
        token_count = len(chunk_text) // 4

        results.append(ChunkResult(
            chunk_id=chunk_id,
            content=chunk_text.strip(),
            chunk_index=i,
            token_count=token_count,
            metadata={
                "document_id": document_id,
                "tenant_id": tenant_id,
                "title": title,
                "source_url": source_url,
                "source_type": source_type,
                "chunk_index": i,
            },
        ))

    logger.info("Chunking complete", document_id=document_id, chunks=len(results))
    return results


def _recursive_split(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Recursively split text using a hierarchy of separators."""
    if not text or len(text) <= chunk_size:
        return [text] if text.strip() else []

    separator = separators[0] if separators else ""
    remaining_separators = separators[1:] if len(separators) > 1 else []

    if separator:
        splits = text.split(separator)
    else:
        # Character-level split
        chunks = []
        for i in range(0, len(text), chunk_size - chunk_overlap):
            chunks.append(text[i : i + chunk_size])
        return chunks

    # Merge splits into chunks of appropriate size
    chunks = []
    current = ""

    for split in splits:
        candidate = current + separator + split if current else split

        if len(candidate) > chunk_size and current:
            chunks.append(current)
            # Keep overlap
            overlap_text = current[-(chunk_overlap):] if len(current) > chunk_overlap else ""
            current = overlap_text + separator + split if overlap_text else split
        else:
            current = candidate

    if current.strip():
        chunks.append(current)

    # Recursively split any chunks that are still too large
    final = []
    for chunk in chunks:
        if len(chunk) > chunk_size and remaining_separators:
            final.extend(_recursive_split(chunk, remaining_separators, chunk_size, chunk_overlap))
        else:
            final.append(chunk)

    return final
