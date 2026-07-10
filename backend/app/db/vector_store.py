from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np
from typing import List, Dict, Tuple

try:
    import faiss
except ImportError as exc:
    raise RuntimeError(
        "faiss-cpu is required. Please install requirements.txt before starting the backend."
    ) from exc


class FaissVectorStore:
    def __init__(
        self,
        dimension: int,
        index_path: Path,
        meta_path: Path,
        metric: str = "cosine",
    ) -> None:
        self.dimension = dimension
        self.index_path = index_path
        self.meta_path = meta_path
        self.metric = metric
        self._lock = threading.RLock()
        self.index: faiss.IndexIDMap2 = self._create_index()

    def _create_index(self) -> faiss.IndexIDMap2:
        base = faiss.IndexFlatIP(self.dimension)
        return faiss.IndexIDMap2(base)

    def load(self) -> None:
        with self._lock:
            if self.index_path.exists():
                self.index = faiss.read_index(str(self.index_path))
            else:
                self.index = self._create_index()

    def persist(self) -> None:
        with self._lock:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            self.meta_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(self.index_path))
            self.meta_path.write_text(
                json.dumps(
                    {
                        "dimension": self.dimension,
                        "metric": self.metric,
                        "ntotal": int(self.index.ntotal),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        array = np.asarray(vectors, dtype=np.float32)
        if self.metric == "cosine":
            faiss.normalize_L2(array)
        return np.ascontiguousarray(array)

    def add(self, ids: List[int], vectors: List[List[float]] | np.ndarray) -> None:
        if not ids:
            return
        with self._lock:
            id_array = np.asarray(ids, dtype=np.int64)
            vector_array = self._normalize(np.asarray(vectors, dtype=np.float32))
            self.index.remove_ids(id_array)
            self.index.add_with_ids(vector_array, id_array)

    def remove(self, ids: List[int]) -> None:
        if not ids:
            return
        with self._lock:
            id_array = np.asarray(ids, dtype=np.int64)
            self.index.remove_ids(id_array)

    def search(self, vector: List[float] | np.ndarray, top_k: int = 5) -> List[Dict[str, float]]:
        with self._lock:
            if self.index.ntotal == 0:
                return []
            query = self._normalize(np.asarray([vector], dtype=np.float32))
            scores, ids = self.index.search(query, top_k)
            results: List[Dict[str, float]] = []
            for item_id, score in zip(ids[0].tolist(), scores[0].tolist()):
                if item_id == -1:
                    continue
                results.append({"id": int(item_id), "score": float(score)})
            return results

    def reset(self) -> None:
        with self._lock:
            self.index = self._create_index()

    def rebuild(self, rows: List[Tuple[int, List[float]]]) -> None:
        with self._lock:
            self.index = self._create_index()
            if rows:
                ids = [row[0] for row in rows]
                vectors = [row[1] for row in rows]
                self.add(ids, vectors)