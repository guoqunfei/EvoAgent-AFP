from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

import httpx

from app.ai.core_ai.base import BaseEmbeddingProvider
from app.core.config import Settings
from typing import List


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_一-鿿]+")


@dataclass
class HashEmbeddingProvider:
    dimension: int
    provider_name: str = "local-hash"
    model_name: str = "local-hash-embedding"

    def _embed(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        tokens = TOKEN_PATTERN.findall(text.lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            for offset in range(0, 16, 4):
                value = int.from_bytes(digest[offset : offset + 4], "little", signed=False)
                index = value % self.dimension
                sign = 1.0 if ((value >> 31) & 1) else -1.0
                vector[index] += sign

        norm = math.sqrt(sum(item * item for item in vector))
        if norm <= 0:
            return vector
        return [item / norm for item in vector]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)


@dataclass
class OpenAICompatibleEmbeddingProvider:
    base_url: str
    api_key: str
    model_name: str
    dimension: int
    timeout_seconds: int = 60
    batch_size: int = 32
    provider_name: str = "openai-compatible"

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model_name, "input": batch},
                timeout=self.timeout_seconds,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Embedding API returned {response.status_code}: {response.text[:500]}"
                )
            data = response.json()["data"]
            all_embeddings.extend(item["embedding"] for item in data)
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]


def build_embedding_provider(settings: Settings) -> BaseEmbeddingProvider:
    if settings.embedding.provider == "openai-compatible":
        if not settings.embedding.base_url or not settings.embedding.api_key:
            raise ValueError("Embedding provider is openai-compatible but base_url/api_key is missing.")
        return OpenAICompatibleEmbeddingProvider(
            base_url=settings.embedding.base_url,
            api_key=settings.embedding.api_key,
            model_name=settings.embedding.model,
            dimension=settings.embedding.dimension,
            timeout_seconds=settings.embedding.timeout_seconds,
            batch_size=settings.embedding.batch_size,
        )
    return HashEmbeddingProvider(
        dimension=settings.embedding.dimension,
        model_name=settings.embedding.model,
    )