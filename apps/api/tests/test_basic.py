"""Basic API tests."""

import pytest
from fastapi.testclient import TestClient


def test_health():
    """Test health endpoint."""
    from src.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "realcore-knowledge-ai-api"


def test_provider_factory():
    """Test provider factory creates correct provider types."""
    from src.providers.base import ChatProvider, EmbeddingProvider
    from src.providers.openai_provider import OpenAIChatProvider, OpenAIEmbeddingProvider
    from src.providers.claude_provider import ClaudeChatProvider

    # Test provider instantiation
    chat_provider = OpenAIChatProvider(api_key="test")
    assert isinstance(chat_provider, ChatProvider)
    assert chat_provider.provider_name == "openai"

    embed_provider = OpenAIEmbeddingProvider(api_key="test")
    assert isinstance(embed_provider, EmbeddingProvider)

    claude_provider = ClaudeChatProvider(api_key="test")
    assert isinstance(claude_provider, ChatProvider)
    assert claude_provider.provider_name == "claude"


def test_chunker():
    """Test document chunking."""
    from src.ingestion.chunker import chunk_document

    content = "This is paragraph one.\n\nThis is paragraph two.\n\nThis is paragraph three."
    chunks = chunk_document(
        document_id="test-doc",
        tenant_id="test-tenant",
        title="Test Document",
        content=content,
        chunk_size=100,
        chunk_overlap=10,
    )
    assert len(chunks) > 0
    assert all(c.content.strip() for c in chunks)
    assert all(c.metadata["tenant_id"] == "test-tenant" for c in chunks)


def test_prompts():
    """Test prompt building."""
    from src.rag.prompts import build_system_prompt, build_context_prompt

    system = build_system_prompt()
    assert "Knowledge Assistant" in system

    chunks = [
        {"title": "Doc 1", "content": "Content here", "source_url": "http://example.com"},
    ]
    context = build_context_prompt(chunks)
    assert "[1]" in context
    assert "Doc 1" in context

    # Empty chunks should return no-answer instruction
    empty_context = build_context_prompt([])
    assert "keine" in empty_context.lower()
