import time
from typing import Iterator, Optional

from openai import OpenAI

from config.settings import settings
from providers.base import BaseProvider, LLMResponse


class OpenAIProvider(BaseProvider):

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._client = OpenAI(api_key=settings.openai_api_key)

    def _build_messages(
        self, prompt: str, system: str, history: Optional[list] = None
    ) -> list:
        messages = [
            {"role": "system", "content": system or "You are a helpful assistant."}
        ]
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

        response = self._client.chat.completions.create(
            model=self.model_id,
            max_tokens=max_tokens,
            messages=self._build_messages(prompt, system, history),
        )

        latency_ms = int((time.time() - start) * 1000)
        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            latency_ms=latency_ms,
            model_id=self.model_id,
            provider="openai",
        )

    def stream(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        history: Optional[list] = None,
    ) -> Iterator[str]:
        response = self._client.chat.completions.create(
            model=self.model_id,
            max_tokens=max_tokens,
            stream=True,
            messages=self._build_messages(prompt, system, history),
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    def is_available(self) -> bool:
        return bool(settings.openai_api_key)
