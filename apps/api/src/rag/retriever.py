"""Retriever — semantic search via Qdrant vector database."""

from __future__ import annotations

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from src.core.config import settings
from src.providers.factory import ProviderFactory

logger = structlog.get_logger()


async def retrieve_chunks(
    query: str,
    tenant_id: str,
    top_k: int = 20,
    score_threshold: float = 0.3,
) -> list[dict]:
    """Retrieve relevant chunks from Qdrant for a given query.

    1. Embed the query using the configured embedding provider
    2. Search Qdrant with tenant filter
    3. Return chunks above score threshold
    """
    # 1. Embed query
    embedding_provider = ProviderFactory.get_embedding_provider()
    embedding_model = ProviderFactory.get_embedding_model()

    try:
        embed_response = await embedding_provider.embed(texts=[query], model=embedding_model)
        query_vector = embed_response.vectors[0]
    except Exception as e:
        logger.error("Query embedding failed", error=str(e))
        return []

    # 2. Search Qdrant
    client = AsyncQdrantClient(url=settings.QDRANT_URL)

    try:
        results = await client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_vector,
            query_filter=Filter(
                must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
            ),
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
    except Exception as e:
        logger.error("Qdrant search failed", error=str(e))
        return []
    finally:
        await client.close()

    # 3. Format results
    chunks = []
    for hit in results:
        payload = hit.payload or {}
        chunks.append({
            "chunk_id": hit.id,
            "content": payload.get("content", ""),
            "document_id": payload.get("document_id", ""),
            "title": payload.get("title", ""),
            "source_url": payload.get("source_url"),
            "source_type": payload.get("source_type"),
            "chunk_index": payload.get("chunk_index", 0),
            "score": hit.score,
        })

    logger.info("Retrieval complete", query_len=len(query), results=len(chunks))
    return chunks
