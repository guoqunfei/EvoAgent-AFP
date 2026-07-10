from __future__ import annotations

from app.crud.base import dump_json, load_json
from app.db.sqlite import SQLiteManager
from typing import List, Dict, Tuple


class DocumentCRUD:
    def __init__(self, sqlite: SQLiteManager) -> None:
        self.sqlite = sqlite

    def create_knowledge_base(self, payload: dict) -> dict:
        sql = """
        INSERT INTO knowledge_bases (
            id, name, slug, description, root_path, metadata_json, created_at, updated_at
        ) VALUES (
            :id, :name, :slug, :description, :root_path, :metadata_json, :created_at, :updated_at
        )
        """
        params = {
            **payload,
            "metadata_json": dump_json(payload.get("metadata")),
        }
        self.sqlite.execute(sql, params)
        return self.get_knowledge_base(payload["id"])

    def list_knowledge_bases(self) -> List[dict]:
        sql = """
        SELECT
            kb.*,
            (SELECT COUNT(*) FROM documents d WHERE d.knowledge_base_id = kb.id) AS document_count,
            (SELECT COUNT(*) FROM chunks c WHERE c.knowledge_base_id = kb.id) AS chunk_count
        FROM knowledge_bases kb
        ORDER BY kb.created_at DESC
        """
        rows = self.sqlite.fetch_all(sql)
        return [self._normalize_kb(row) for row in rows]

    def get_knowledge_base(self, kb_id: str) -> dict | None:
        sql = """
        SELECT
            kb.*,
            (SELECT COUNT(*) FROM documents d WHERE d.knowledge_base_id = kb.id) AS document_count,
            (SELECT COUNT(*) FROM chunks c WHERE c.knowledge_base_id = kb.id) AS chunk_count
        FROM knowledge_bases kb
        WHERE kb.id = :kb_id
        """
        row = self.sqlite.fetch_one(sql, {"kb_id": kb_id})
        return self._normalize_kb(row) if row else None

    def get_knowledge_base_by_slug(self, slug: str) -> dict | None:
        row = self.sqlite.fetch_one("SELECT * FROM knowledge_bases WHERE slug = :slug", {"slug": slug})
        return self._normalize_kb(row) if row else None

    def upsert_document(self, payload: dict) -> dict:
        existing = self.sqlite.fetch_one(
            """
            SELECT * FROM documents
            WHERE knowledge_base_id = :knowledge_base_id AND source_path = :source_path
            """,
            {"knowledge_base_id": payload["knowledge_base_id"], "source_path": payload["source_path"]},
        )
        params = {
            **payload,
            "metadata_json": dump_json(payload.get("metadata")),
        }
        if existing:
            self.sqlite.execute(
                """
                UPDATE documents
                SET title = :title,
                    checksum = :checksum,
                    content = :content,
                    metadata_json = :metadata_json,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                {
                    **params,
                    "id": existing["id"],
                },
            )
            return self.get_document(existing["id"])

        self.sqlite.execute(
            """
            INSERT INTO documents (
                id, knowledge_base_id, source_type, source_path, title, checksum, content,
                metadata_json, created_at, updated_at
            ) VALUES (
                :id, :knowledge_base_id, :source_type, :source_path, :title, :checksum, :content,
                :metadata_json, :created_at, :updated_at
            )
            """,
            params,
        )
        return self.get_document(payload["id"])

    def get_document(self, document_id: str) -> dict | None:
        row = self.sqlite.fetch_one("SELECT * FROM documents WHERE id = :document_id", {"document_id": document_id})
        return self._normalize_document(row) if row else None

    def list_documents(self, knowledge_base_id: str) -> List[dict]:
        rows = self.sqlite.fetch_all(
            "SELECT * FROM documents WHERE knowledge_base_id = :knowledge_base_id ORDER BY updated_at DESC",
            {"knowledge_base_id": knowledge_base_id},
        )
        return [self._normalize_document(row) for row in rows]

    def get_chunk_vector_ids_by_document(self, document_id: str) -> List[int]:
        rows = self.sqlite.fetch_all(
            "SELECT vector_id FROM chunks WHERE document_id = :document_id",
            {"document_id": document_id},
        )
        return [int(row["vector_id"]) for row in rows]

    def replace_chunks(self, document_id: str, chunk_payloads: List[dict]) -> None:
        statements: List[Tuple[str, dict | None]] = [
            ("DELETE FROM chunks WHERE document_id = :document_id", {"document_id": document_id})
        ]
        for payload in chunk_payloads:
            statements.append(
                (
                    """
                    INSERT INTO chunks (
                        id, document_id, knowledge_base_id, vector_id, chunk_index, text, token_count,
                        metadata_json, embedding_model, embedding_dim, created_at
                    ) VALUES (
                        :id, :document_id, :knowledge_base_id, :vector_id, :chunk_index, :text, :token_count,
                        :metadata_json, :embedding_model, :embedding_dim, :created_at
                    )
                    """,
                    {
                        **payload,
                        "metadata_json": dump_json(payload.get("metadata")),
                    },
                )
            )
        self.sqlite.transaction(statements)

    def list_chunks(self, knowledge_base_id: str, limit: int = 50, offset: int = 0) -> List[dict]:
        rows = self.sqlite.fetch_all(
            """
            SELECT c.*, d.title AS document_title, d.source_path
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.knowledge_base_id = :knowledge_base_id
            ORDER BY c.created_at DESC
            LIMIT :limit OFFSET :offset
            """,
            {"knowledge_base_id": knowledge_base_id, "limit": limit, "offset": offset},
        )
        return [self._normalize_chunk(row) for row in rows]

    def get_chunks_by_vector_ids(self, vector_ids: List[int]) -> List[dict]:
        if not vector_ids:
            return []
        placeholders = ",".join(["?"] * len(vector_ids))
        sql = f"""
        SELECT c.*, d.title AS document_title, d.source_path
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.vector_id IN ({placeholders})
        """
        rows = self.sqlite.fetch_all(sql, tuple(vector_ids))
        return [self._normalize_chunk(row) for row in rows]

    def keyword_search_chunks(
        self,
        terms: List[str],
        knowledge_base_ids: List[str] | None = None,
        limit: int = 12,
    ) -> List[dict]:
        clean_terms = [term.strip().lower() for term in terms if term.strip()]
        if not clean_terms:
            return []

        conditions = []
        params: Dict[str, object] = {"limit": limit}
        for index, term in enumerate(clean_terms[:5]):
            key = f"term_{index}"
            conditions.append(f"LOWER(c.text) LIKE :{key}")
            params[key] = f"%{term}%"

        kb_filter = ""
        if knowledge_base_ids:
            kb_placeholders = ",".join([f":kb_{index}" for index in range(len(knowledge_base_ids))])
            kb_filter = f" AND c.knowledge_base_id IN ({kb_placeholders})"
            params.update({f"kb_{index}": kb_id for index, kb_id in enumerate(knowledge_base_ids)})

        sql = f"""
        SELECT c.*, d.title AS document_title, d.source_path
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE ({' OR '.join(conditions)}) {kb_filter}
        ORDER BY c.created_at DESC
        LIMIT :limit
        """
        rows = self.sqlite.fetch_all(sql, params)
        return [self._normalize_chunk(row) for row in rows]

    def get_all_chunks(self) -> List[dict]:
        rows = self.sqlite.fetch_all(
            "SELECT * FROM chunks ORDER BY created_at ASC"
        )
        return [self._normalize_chunk(row) for row in rows]

    def _normalize_kb(self, row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            **row,
            "metadata": load_json(row.get("metadata_json"), {}),
        }

    def _normalize_document(self, row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            **row,
            "metadata": load_json(row.get("metadata_json"), {}),
        }

    def _normalize_chunk(self, row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            **row,
            "metadata": load_json(row.get("metadata_json"), {}),
        }