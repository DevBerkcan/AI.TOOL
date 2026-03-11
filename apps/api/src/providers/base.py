"""AI Provider Layer — Abstract interfaces for model providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


# ── Data Models ──────────────────────────────────────────────────────────
@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ChatResponse:
    content: str
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    provider: str = ""


@dataclass
class StreamChunk:
    delta: str = ""
    done: bool = False
    usage: Usage | None = None


@dataclass
class EmbeddingResponse:
    vectors: list[list[float]] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    model: str = ""


@dataclass
class RerankResult:
    index: int
    score: float


# ── Provider Protocols ───────────────────────────────────────────────────
class ChatProvider(ABC):
    """Interface for chat completion providers."""

    provider_name: str = "unknown"

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> ChatResponse:
        """Generate a chat completion."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion."""
        ...


class EmbeddingProvider(ABC):
    """Interface for embedding providers."""

    provider_name: str = "unknown"

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        model: str,
    ) -> EmbeddingResponse:
        """Generate embeddings for a list of texts."""
        ...


class RerankProvider(ABC):
    """Interface for reranking providers."""

    provider_name: str = "unknown"

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[str],
        model: str,
        top_n: int = 5,
    ) -> list[RerankResult]:
        """Rerank documents by relevance to query."""
        ...
