"""Anthropic Claude provider for chat completion."""

from __future__ import annotations

from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from src.providers.base import (
    ChatProvider,
    ChatResponse,
    Message,
    StreamChunk,
    Usage,
)


class ClaudeChatProvider(ChatProvider):
    """Anthropic Claude Chat Completion provider."""

    provider_name = "claude"

    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> ChatResponse:
        # Extract system message (Claude handles it separately)
        system = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=chat_messages,
            temperature=temperature,
        )

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return ChatResponse(
            content=content,
            usage=Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            model=response.model,
            provider=self.provider_name,
        )

    async def stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[StreamChunk]:
        system = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        async with self.client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=chat_messages,
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(delta=text)

            # Final message with usage
            final = await stream.get_final_message()
            yield StreamChunk(
                done=True,
                usage=Usage(
                    input_tokens=final.usage.input_tokens,
                    output_tokens=final.usage.output_tokens,
                ),
            )
