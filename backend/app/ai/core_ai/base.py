from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Protocol
from typing import Optional, List, Dict


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatResult:
    text: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    raw: dict | None = None


@dataclass
class ChatStreamChunk:
    """A single chunk of a streaming chat response."""
    content: str
    finish_reason: Optional[str] = None


class BaseEmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimension: int

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        ...

    def embed_query(self, text: str) -> List[float]:
        ...


class BaseChatProvider(Protocol):
    provider_name: str
    model_name: str

    def generate(
        self,
        messages: List[ChatMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> ChatResult:
        ...

    def generate_stream(
        self,
        messages: List[ChatMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Iterator[ChatStreamChunk]:
        """Stream chat response as an iterator of chunks."""
        ...