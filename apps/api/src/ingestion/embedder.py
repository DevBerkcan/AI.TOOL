"""Embedding service — vectorize chunks and upsert into Qdrant."""

from __future__ import annotations

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.core.config import settings
from src.ingestion.chunker import ChunkResult
from src.providers.factory import ProviderFactory

logger = structlog.get_logger()

BATCH_SIZE = 100
VECTOR_SIZE = 1536  # text-embedding-3-small


async def ensure_collection():
    """Create Qdrant collection if it doesn't exist."""
    client = AsyncQdrantClient(url=settings.QDRANT_URL)
    try:
        collections = await client.get_collections()
        names = [c.name for c in collections.collections]
        if settings.QDRANT_COLLECTION not in names:
            await client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection", name=settings.QDRANT_COLLECTION)
    finally:
        await client.close()


async def embed_and_index_chunks(chunks: list[ChunkResult]) -> int:
    """Embed chunks and upsert into Qdrant. Returns count of indexed chunks."""
    if not chunks:
        return 0

    provider = ProviderFactory.get_embedding_provider()
    model = ProviderFactory.get_embedding_model()
    client = AsyncQdrantClient(url=settings.QDRANT_URL)
    indexed = 0

    try:
        await ensure_collection()

        # Process in batches
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            texts = [c.content for c in batch]

            # Get embeddings
            response = await provider.embed(texts=texts, model=model)

            # Build Qdrant points
            points = []
            for chunk, vector in zip(batch, response.vectors):
                points.append(PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload={
                        "content": chunk.content,
                        "token_count": chunk.token_count,
                        **chunk.metadata,
                    },
                ))

            # Upsert to Qdrant
            await client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=points,
            )
            indexed += len(points)

        logger.info("Embedding complete", total=indexed)

    except Exception as e:
        logger.error("Embedding failed", error=str(e), indexed_so_far=indexed)
        raise
    finally:
        await client.close()

    return indexed
