"""Azure OpenAI provider for chat and embeddings."""

from __future__ import annotations

from typing import AsyncIterator

from openai import AsyncAzureOpenAI

from src.providers.base import (
    ChatProvider, ChatResponse, EmbeddingProvider, EmbeddingResponse,
    Message, StreamChunk, Usage,
)


class AzureOpenAIChatProvider(ChatProvider):
    """Azure OpenAI Chat Completion provider."""

    provider_name = "azure_openai"

    def __init__(self, api_key: str, endpoint: str, api_version: str = "2024-06-01"):
        self.client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )

    async def complete(
        self, messages: list[Message], model: str,
        temperature: float = 0.7, max_tokens: int = 2000,
    ) -> ChatResponse:
        response = await self.client.chat.completions.create(
            model=model,  # This is the deployment name in Azure
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        usage = response.usage

        return ChatResponse(
            content=choice.message.content or "",
            usage=Usage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            ),
            model=response.model,
            provider=self.provider_name,
        )

    async def stream(
        self, messages: list[Message], model: str,
        temperature: float = 0.7, max_tokens: int = 2000,
    ) -> AsyncIterator[StreamChunk]:
        stream = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield StreamChunk(delta=chunk.choices[0].delta.content)
            if chunk.usage:
                yield StreamChunk(
                    done=True,
                    usage=Usage(
                        input_tokens=chunk.usage.prompt_tokens,
                        output_tokens=chunk.usage.completion_tokens,
                    ),
                )


class AzureOpenAIEmbeddingProvider(EmbeddingProvider):
    """Azure OpenAI Embeddings provider."""

    provider_name = "azure_openai"

    def __init__(self, api_key: str, endpoint: str, api_version: str = "2024-06-01"):
        self.client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )

    async def embed(self, texts: list[str], model: str) -> EmbeddingResponse:
        response = await self.client.embeddings.create(model=model, input=texts)
        vectors = [item.embedding for item in response.data]
        return EmbeddingResponse(
            vectors=vectors,
            usage=Usage(input_tokens=response.usage.prompt_tokens if response.usage else 0),
            model=response.model,
        )
