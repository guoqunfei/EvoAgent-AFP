from __future__ import annotations

from app.utils.text import normalize_whitespace
from typing import List


def estimate_token_count(text: str) -> int:
    return max(1, len(text) // 4)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 180) -> List[str]:
    content = normalize_whitespace(text)
    if not content:
        return []
    if len(content) <= chunk_size:
        return [content]

    chunks: List[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(content):
        end = min(len(content), start + chunk_size)
        chunk = content[start:end]
        if end < len(content):
            last_break = max(chunk.rfind("。"), chunk.rfind("."), chunk.rfind(" "), chunk.rfind("\n"))
            if last_break > chunk_size * 0.6:
                chunk = chunk[: last_break + 1]
                end = start + len(chunk)
        chunks.append(chunk.strip())
        if end >= len(content):
            break
        start = max(start + step, end - overlap)
    return [item for item in chunks if item]