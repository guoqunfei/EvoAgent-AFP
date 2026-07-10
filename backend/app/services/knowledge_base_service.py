from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from app.ai.core_ai.base import BaseEmbeddingProvider
from app.core.config import Settings
from app.crud.documents import DocumentCRUD
from app.db.vector_store import FaissVectorStore
from app.exceptions.errors import ConflictError, NotFoundError
from app.utils.chunking import chunk_text, estimate_token_count
from app.utils.files import list_files
from app.utils.hash import sha256_text
from app.utils.ids import new_id, slugify, stable_int_id
from app.utils.text import strip_html
from app.utils.time import utc_now_iso
from typing import Optional, List, Tuple


class KnowledgeBaseService:
    def __init__(
        self,
        *,
        settings: Settings,
        document_crud: DocumentCRUD,
        embedding_provider: BaseEmbeddingProvider,
        vector_store: FaissVectorStore,
    ) -> None:
        self.settings = settings
        self.document_crud = document_crud
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def list_knowledge_bases(self) -> List[dict]:
        return self.document_crud.list_knowledge_bases()

    def get_knowledge_base(self, kb_id: str) -> dict:
        kb = self.document_crud.get_knowledge_base(kb_id)
        if not kb:
            raise NotFoundError("Knowledge base not found", details={"knowledge_base_id": kb_id})
        return kb

    def create_knowledge_base(
        self,
        *,
        name: str,
        slug: Optional[str] = None,
        description: str = "",
        root_path: Optional[str] = None,
        metadata: dict | None = None,
    ) -> dict:
        target_slug = slug or slugify(name)
        if self.document_crud.get_knowledge_base_by_slug(target_slug):
            raise ConflictError("Knowledge base slug already exists", details={"slug": target_slug})
        now = utc_now_iso()
        return self.document_crud.create_knowledge_base(
            {
                "id": new_id("kb"),
                "name": name,
                "slug": target_slug,
                "description": description,
                "root_path": root_path or "",
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now,
            }
        )

    def list_documents(self, kb_id: str) -> List[dict]:
        self.get_knowledge_base(kb_id)
        return self.document_crud.list_documents(kb_id)

    def list_chunks(self, kb_id: str, limit: int = 50, offset: int = 0) -> List[dict]:
        self.get_knowledge_base(kb_id)
        return self.document_crud.list_chunks(kb_id, limit=limit, offset=offset)

    def ingest_path(self, kb_id: str, raw_path: str, recursive: bool = True, source_type: str = "local_file") -> dict:
        kb = self.get_knowledge_base(kb_id)
        resolved_path = self._resolve_path(raw_path)
        suffixes = set(self.settings.knowledge_base.allowed_suffixes)
        files = list_files(resolved_path, suffixes=suffixes, recursive=recursive)
        errors: List[str] = []
        document_count = 0
        chunk_count = 0

        for file_path in files:
            try:
                result = self._ingest_file(kb=kb, file_path=file_path, source_type=source_type)
                document_count += 1
                chunk_count += result["chunk_count"]
            except Exception as exc:
                errors.append(f"{file_path}: {exc}")

        return {
            "knowledge_base_id": kb_id,
            "files_seen": len(files),
            "documents_written": document_count,
            "chunks_written": chunk_count,
            "errors": errors,
        }

    def ingest_text(
        self,
        kb_id: str,
        *,
        title: str,
        text: str,
        source_path: Optional[str] = None,
        metadata: dict | None = None,
    ) -> dict:
        kb = self.get_knowledge_base(kb_id)
        return self._store_document(
            kb=kb,
            title=title,
            text=text,
            source_path=source_path or f"inline://{title}",
            source_type="inline_text",
            metadata=metadata or {},
        )

    def ingest_upload(self, kb_id: str, *, file_name: str, file_bytes: bytes) -> dict:
        kb = self.get_knowledge_base(kb_id)
        suffix = Path(file_name).suffix.lower()
        allowed = set(self.settings.knowledge_base.allowed_suffixes)
        if suffix not in allowed:
            raise ValueError(f"Unsupported file type: {suffix}. Allowed: {sorted(allowed)}")

        uploads_dir = self.settings.resolve_backend_path(self.settings.knowledge_base.uploads_dir)
        dest_path = uploads_dir / file_name
        dest_path.write_bytes(file_bytes)

        result = self._ingest_file(kb=kb, file_path=dest_path, source_type="upload")
        result["knowledge_base_id"] = kb_id
        return result

    def rebuild_index(self) -> dict:
        rows = self.document_crud.get_all_chunks()
        texts = [row["text"] for row in rows]
        vectors = self.embedding_provider.embed_texts(texts) if texts else []
        records = [(int(row["vector_id"]), vectors[index]) for index, row in enumerate(rows)]
        self.vector_store.rebuild(records)
        self.vector_store.persist()
        return {"chunks_indexed": len(records), "dimension": self.embedding_provider.dimension}

    def _ingest_file(self, *, kb: dict, file_path: Path, source_type: str) -> dict:
        title, text, metadata = self._load_file(file_path)
        metadata.update({"absolute_path": str(file_path.resolve())})
        return self._store_document(
            kb=kb,
            title=title,
            text=text,
            source_path=str(file_path),
            source_type=source_type,
            metadata=metadata,
        )

    def _store_document(
        self,
        *,
        kb: dict,
        title: str,
        text: str,
        source_path: str,
        source_type: str,
        metadata: dict,
    ) -> dict:
        checksum = sha256_text(text)
        now = utc_now_iso()
        document_id = new_id("doc")
        existing = self.document_crud.upsert_document(
            {
                "id": document_id,
                "knowledge_base_id": kb["id"],
                "source_type": source_type,
                "source_path": source_path,
                "title": title,
                "checksum": checksum,
                "content": text,
                "metadata": metadata,
                "created_at": now,
                "updated_at": now,
            }
        )

        old_vector_ids = self.document_crud.get_chunk_vector_ids_by_document(existing["id"])
        self.vector_store.remove(old_vector_ids)

        chunk_texts = chunk_text(
            text,
            chunk_size=self.settings.rag.chunk_size,
            overlap=self.settings.rag.chunk_overlap,
        )
        vectors = self.embedding_provider.embed_texts(chunk_texts) if chunk_texts else []

        chunk_payloads: List[dict] = []
        vector_ids: List[int] = []
        for index, chunk_value in enumerate(chunk_texts):
            chunk_id = new_id("chk")
            vector_id = stable_int_id(chunk_id)
            vector_ids.append(vector_id)
            chunk_payloads.append(
                {
                    "id": chunk_id,
                    "document_id": existing["id"],
                    "knowledge_base_id": kb["id"],
                    "vector_id": vector_id,
                    "chunk_index": index,
                    "text": chunk_value,
                    "token_count": estimate_token_count(chunk_value),
                    "metadata": {
                        "title": title,
                        "source_path": source_path,
                        "chunk_index": index,
                    },
                    "embedding_model": self.embedding_provider.model_name,
                    "embedding_dim": self.embedding_provider.dimension,
                    "created_at": now,
                }
            )

        self.document_crud.replace_chunks(existing["id"], chunk_payloads)
        self.vector_store.add(vector_ids, vectors)
        self.vector_store.persist()

        return {
            "document_id": existing["id"],
            "title": title,
            "chunk_count": len(chunk_payloads),
            "checksum": checksum,
        }

    def _load_file(self, file_path: Path) -> Tuple[str, str, dict]:
        suffix = file_path.suffix.lower()
        if suffix in {".md", ".txt"}:
            text = file_path.read_text(encoding="utf-8")
        elif suffix == ".json":
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            text = json.dumps(payload, ensure_ascii=False, indent=2)
        elif suffix == ".html":
            text = strip_html(file_path.read_text(encoding="utf-8"))
        elif suffix == ".pdf":
            try:
                reader = PdfReader(str(file_path))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                text = file_path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file suffix: {suffix}")

        return (
            file_path.stem,
            text,
            {
                "suffix": suffix,
                "size_bytes": file_path.stat().st_size,
            },
        )

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return self.settings.resolve_backend_path(raw_path)