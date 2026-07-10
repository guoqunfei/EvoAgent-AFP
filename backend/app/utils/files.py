from __future__ import annotations

from pathlib import Path
from typing import List


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_files(base_path: Path, suffixes: set[str], recursive: bool = True) -> List[Path]:
    if base_path.is_file():
        return [base_path] if base_path.suffix.lower() in suffixes else []
    if not base_path.exists():
        return []
    pattern = "**/*" if recursive else "*"
    return [path for path in base_path.glob(pattern) if path.is_file() and path.suffix.lower() in suffixes]