"""Reranker — rerank chunks by relevance using cross-encoder or score-based fallback."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


async def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """Rerank retrieved chunks. Falls back to vector score ranking if no reranker configured.

    In Phase 2, this will integrate with Cohere Rerank or a local cross-encoder model.
    For MVP, we use the vector similarity score directly.
    """
    if not chunks:
        return []

    # MVP: sort by vector score (descending) and take top_n
    sorted_chunks = sorted(chunks, key=lambda c: c.get("score", 0), reverse=True)
    result = sorted_chunks[:top_n]

    logger.info("Reranking complete", input=len(chunks), output=len(result), method="vector_score")
    return result
