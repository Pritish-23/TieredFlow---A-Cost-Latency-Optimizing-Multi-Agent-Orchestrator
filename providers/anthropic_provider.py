import time
from typing import Iterator, Optional

import anthropic

from config.settings import settings
from providers.base import BaseProvider, LLMResponse


class AnthropicProvider(BaseProvider):

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _build_messages(self, prompt: str, history: Optional[list] = None) -> list:
        messages = []
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})
        return messages

    def call(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        history: Optional[list] = None,
    ) -> LLMResponse:
        start = time.time()

        message = self._client.messages.create(
            model=self.model_id,
            max_tokens=max_tokens,
            system=system or "You are a helpful assistant.",
            messages=self._build_messages(prompt, history),
        )

        latency_ms = int((time.time() - start) * 1000)

        return LLMResponse(
            content=message.content[0].text,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            latency_ms=latency_ms,
            model_id=self.model_id,
            provider="anthropic",
        )

    def stream(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        history: Optional[list] = None,
    ) -> Iterator[str]:
        with self._client.messages.stream(
            model=self.model_id,
            max_tokens=max_tokens,
            system=system or "You are a helpful assistant.",
            messages=self._build_messages(prompt, history),
        ) as stream:
            for text in stream.text_stream:
                yield text

    def is_available(self) -> bool:
        return bool(settings.anthropic_api_key)
