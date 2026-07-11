import time

import anthropic

from config.settings import settings
from providers.base import BaseProvider, LLMResponse


class AnthropicProvider(BaseProvider):

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def call(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
    ) -> LLMResponse:
        start = time.time()

        message = self._client.messages.create(
            model=self.model_id,
            max_tokens=max_tokens,
            system=system or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}],
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

    def is_available(self) -> bool:
        return bool(settings.anthropic_api_key)
