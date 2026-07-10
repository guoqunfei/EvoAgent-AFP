from __future__ import annotations

import json
from typing import Any
from typing import Optional


def dump_json(data: Any) -> str:
    return json.dumps(data or {}, ensure_ascii=False)


def load_json(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    return json.loads(raw)