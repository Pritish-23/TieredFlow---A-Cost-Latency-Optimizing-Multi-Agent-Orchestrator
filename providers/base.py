from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional


@dataclass
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model_id: str
    provider: str


class BaseProvider(ABC):

    @abstractmethod
    def call(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        history: Optional[list] = None,
    ) -> LLMResponse: ...

    @abstractmethod
    def stream(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        history: Optional[list] = None,
    ) -> Iterator[str]: ...

    @abstractmethod
    def is_available(self) -> bool: ...
