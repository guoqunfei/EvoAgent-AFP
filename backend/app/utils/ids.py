from __future__ import annotations

import hashlib
import re
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def slugify(text: str) -> str:
    value = re.sub(r"[^\w一-鿿-]+", "-", text.strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or uuid4().hex[:8]


def stable_int_id(raw: str) -> int:
    digest = hashlib.blake2b(raw.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big", signed=False)
    return value & 0x7FFF_FFFF_FFFF_FFFF