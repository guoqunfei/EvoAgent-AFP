from __future__ import annotations

from app.crud.base import dump_json, load_json
from app.db.sqlite import SQLiteManager
from typing import Optional, List


class ChatCRUD:
    def __init__(self, sqlite: SQLiteManager) -> None:
        self.sqlite = sqlite

    def create_session(self, payload: dict) -> dict:
        self.sqlite.execute(
            """
            INSERT INTO chat_sessions (id, title, system_prompt, metadata_json, created_at, updated_at)
            VALUES (:id, :title, :system_prompt, :metadata_json, :created_at, :updated_at)
            """,
            {
                **payload,
                "metadata_json": dump_json(payload.get("metadata")),
            },
        )
        return self.get_session(payload["id"])

    def get_session(self, session_id: str) -> dict | None:
        row = self.sqlite.fetch_one(
            "SELECT * FROM chat_sessions WHERE id = :session_id",
            {"session_id": session_id},
        )
        if not row:
            return None
        return {
            **row,
            "metadata": load_json(row.get("metadata_json"), {}),
        }

    def list_sessions(self) -> List[dict]:
        rows = self.sqlite.fetch_all("SELECT * FROM chat_sessions ORDER BY updated_at DESC")
        return [
            {
                **row,
                "metadata": load_json(row.get("metadata_json"), {}),
            }
            for row in rows
        ]

    def touch_session(self, session_id: str, updated_at: str, title: Optional[str] = None) -> None:
        if title:
            self.sqlite.execute(
                "UPDATE chat_sessions SET title = :title, updated_at = :updated_at WHERE id = :session_id",
                {"title": title, "updated_at": updated_at, "session_id": session_id},
            )
            return
        self.sqlite.execute(
            "UPDATE chat_sessions SET updated_at = :updated_at WHERE id = :session_id",
            {"updated_at": updated_at, "session_id": session_id},
        )

    def add_message(self, payload: dict) -> dict:
        self.sqlite.execute(
            """
            INSERT INTO chat_messages (id, session_id, role, content, metadata_json, created_at)
            VALUES (:id, :session_id, :role, :content, :metadata_json, :created_at)
            """,
            {
                **payload,
                "metadata_json": dump_json(payload.get("metadata")),
            },
        )
        return self.get_message(payload["id"])

    def get_message(self, message_id: str) -> dict | None:
        row = self.sqlite.fetch_one("SELECT * FROM chat_messages WHERE id = :message_id", {"message_id": message_id})
        if not row:
            return None
        return {
            **row,
            "metadata": load_json(row.get("metadata_json"), {}),
        }

    def list_messages(self, session_id: str) -> List[dict]:
        rows = self.sqlite.fetch_all(
            "SELECT * FROM chat_messages WHERE session_id = :session_id ORDER BY created_at ASC",
            {"session_id": session_id},
        )
        return [
            {
                **row,
                "metadata": load_json(row.get("metadata_json"), {}),
            }
            for row in rows
        ]