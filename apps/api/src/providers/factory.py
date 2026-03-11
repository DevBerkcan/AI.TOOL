"""Provider factory with fallback and circuit breaker logic."""

from __future__ import annotations

import time

import structlog

from src.core.config import settings
from src.providers.azure_openai_provider import (
    AzureOpenAIChatProvider,
    AzureOpenAIEmbeddingProvider,
)
from src.providers.base import (
    ChatProvider,
    ChatResponse,
    EmbeddingProvider,
    Message,
)
from src.providers.claude_provider import ClaudeChatProvider
from src.providers.openai_provider import OpenAIChatProvider, OpenAIEmbeddingProvider

logger = structlog.get_logger()


# ── Circuit Breaker ──────────────────────────────────────────────────────
class CircuitBreaker:
    """Simple circuit breaker for provider health tracking."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures: dict[str, int] = {}
        self._open_since: dict[str, float] = {}

    def is_open(self, provider_name: str) -> bool:
        """Check if circuit is open (provider is down)."""
        if provider_name not in self._open_since:
            return False
        elapsed = time.time() - self._open_since[provider_name]
        if elapsed > self.recovery_timeout:
            # Half-open: allow a retry
            del self._open_since[provider_name]
            self._failures[provider_name] = 0
            return False
        return True

    def record_failure(self, provider_name: str):
        self._failures[provider_name] = self._failures.get(provider_name, 0) + 1
        if self._failures[provider_name] >= self.failure_threshold:
            self._open_since[provider_name] = time.time()
            logger.warning("Circuit breaker opened", provider=provider_name)

    def record_success(self, provider_name: str):
        self._failures[provider_name] = 0
        if provider_name in self._open_since:
            del self._open_since[provider_name]


circuit_breaker = CircuitBreaker()


# ── Factory ──────────────────────────────────────────────────────────────
class ProviderFactory:
    """Creates and manages AI provider instances."""

    @staticmethod
    def get_chat_provider(provider_name: str | None = None) -> ChatProvider:
        """Get a chat provider by name."""
        name = provider_name or settings.DEFAULT_CHAT_PROVIDER

        if name == "openai":
            return OpenAIChatProvider(api_key=settings.OPENAI_API_KEY)
        elif name == "azure_openai":
            return AzureOpenAIChatProvider(
                api_key=settings.AZURE_OPENAI_API_KEY,
                endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )
        elif name == "claude":
            return ClaudeChatProvider(api_key=settings.ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Unknown chat provider: {name}")

    @staticmethod
    def get_embedding_provider(provider_name: str | None = None) -> EmbeddingProvider:
        """Get an embedding provider by name."""
        name = provider_name or settings.DEFAULT_EMBEDDING_PROVIDER

        if name == "openai":
            return OpenAIEmbeddingProvider(api_key=settings.OPENAI_API_KEY)
        elif name == "azure_openai":
            return AzureOpenAIEmbeddingProvider(
                api_key=settings.AZURE_OPENAI_API_KEY,
                endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )
        else:
            raise ValueError(f"Unknown embedding provider: {name}")

    @staticmethod
    def get_chat_model(provider_name: str | None = None) -> str:
        """Get the default model name for a provider."""
        name = provider_name or settings.DEFAULT_CHAT_PROVIDER
        if name == "openai":
            return settings.OPENAI_CHAT_MODEL
        elif name == "azure_openai":
            return settings.AZURE_OPENAI_CHAT_DEPLOYMENT
        elif name == "claude":
            return settings.ANTHROPIC_CHAT_MODEL
        return "gpt-4o"

    @staticmethod
    def get_embedding_model(provider_name: str | None = None) -> str:
        """Get the default embedding model name."""
        name = provider_name or settings.DEFAULT_EMBEDDING_PROVIDER
        if name == "openai":
            return settings.OPENAI_EMBEDDING_MODEL
        elif name == "azure_openai":
            return settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        return "text-embedding-3-small"


# ── Resilient Provider (with fallback) ───────────────────────────────────
FALLBACK_ORDER = ["openai", "azure_openai", "claude"]


async def get_chat_completion_with_fallback(
    messages: list[Message],
    primary_provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> ChatResponse:
    """Try primary provider, fallback on failure."""
    primary = primary_provider or settings.DEFAULT_CHAT_PROVIDER
    providers_to_try = [primary] + [p for p in FALLBACK_ORDER if p != primary]

    last_error = None
    for provider_name in providers_to_try:
        if circuit_breaker.is_open(provider_name):
            logger.info("Skipping provider (circuit open)", provider=provider_name)
            continue

        try:
            provider = ProviderFactory.get_chat_provider(provider_name)
            m = model or ProviderFactory.get_chat_model(provider_name)
            result = await provider.complete(messages, m, temperature, max_tokens)
            circuit_breaker.record_success(provider_name)

            if provider_name != primary:
                logger.warning("Used fallback provider", primary=primary, fallback=provider_name)

            return result

        except Exception as e:
            circuit_breaker.record_failure(provider_name)
            logger.error("Provider failed", provider=provider_name, error=str(e))
            last_error = e

    raise last_error or RuntimeError("All providers failed")
