from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import List


SPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[A-Za-z0-9_一-鿿]+")


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def normalize_whitespace(text: str) -> str:
    return SPACE_RE.sub(" ", text).strip()


def strip_html(raw_html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(raw_html)
    return normalize_whitespace(html.unescape(parser.text()))


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def keyword_overlap_score(query: str, text: str) -> float:
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(tokenize(text))
    return len(query_tokens & text_tokens) / max(len(query_tokens), 1)