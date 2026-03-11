"""RAG Pipeline — orchestrates retrieval → rerank → prompt → generate."""

from __future__ import annotations

import json
import time
import uuid
from typing import AsyncIterator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.providers.base import Message
from src.providers.factory import ProviderFactory
from src.rag.prompts import build_system_prompt, build_context_prompt, NO_ANSWER_INSTRUCTION
from src.rag.retriever import retrieve_chunks
from src.rag.reranker import rerank_chunks

logger = structlog.get_logger()


class RAGPipeline:
    """Full RAG pipeline: query → retrieval → rerank → prompt → stream answer."""

    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def run(self, query: str, conversation_id: uuid.UUID) -> AsyncIterator[dict]:
        """Execute the RAG pipeline and yield SSE events."""
        start = time.perf_counter()

        # 1. Retrieve relevant chunks
        yield {"event": "status", "data": json.dumps({"step": "retrieving"})}
        chunks = await retrieve_chunks(
            query=query,
            tenant_id=self.tenant_id,
            top_k=20,
        )

        if not chunks:
            yield {"event": "token", "data": json.dumps({"token": "Ich konnte leider keine relevanten Dokumente zu deiner Frage finden. Bitte stelle sicher, dass die entsprechenden Quellen bereits synchronisiert wurden."})}
            yield {"event": "done", "data": json.dumps({"sources": []})}
            return

        # 2. Rerank
        yield {"event": "status", "data": json.dumps({"step": "reranking"})}
        reranked = await rerank_chunks(query=query, chunks=chunks, top_n=5)

        # 3. Build prompt
        system_prompt = build_system_prompt()
        context_prompt = build_context_prompt(reranked)

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=f"{context_prompt}\n\nFrage: {query}"),
        ]

        # 4. Stream answer
        yield {"event": "status", "data": json.dumps({"step": "generating"})}

        provider = ProviderFactory.get_chat_provider()
        model = ProviderFactory.get_chat_model()
        full_answer = ""
        usage = None

        try:
            async for chunk in provider.stream(messages, model=model, temperature=0.3, max_tokens=2000):
                if chunk.delta:
                    full_answer += chunk.delta
                    yield {"event": "token", "data": json.dumps({"token": chunk.delta})}
                if chunk.done and chunk.usage:
                    usage = chunk.usage
        except Exception as e:
            logger.error("Generation error", error=str(e))
            yield {"event": "error", "data": json.dumps({"error": "Generation failed"})}
            return

        # 5. Build source references
        sources = [
            {
                "document_id": c.get("document_id", ""),
                "title": c.get("title", "Unknown"),
                "source_url": c.get("source_url"),
                "snippet": c.get("content", "")[:200],
                "score": c.get("score", 0),
            }
            for c in reranked
        ]

        latency_ms = int((time.perf_counter() - start) * 1000)

        # 6. Save to query history
        from src.models.entities import QueryHistory
        qh = QueryHistory(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            conversation_id=conversation_id,
            query_text=query,
            answer_text=full_answer,
            sources=sources,
            model_used=model,
            provider_used=provider.provider_name,
            tokens_input=usage.input_tokens if usage else 0,
            tokens_output=usage.output_tokens if usage else 0,
            latency_ms=latency_ms,
        )
        self.db.add(qh)

        yield {"event": "done", "data": json.dumps({"sources": sources, "query_id": str(qh.id)})}
