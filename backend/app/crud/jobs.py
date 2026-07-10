from __future__ import annotations

from app.crud.base import dump_json, load_json
from app.db.sqlite import SQLiteManager
from typing import Optional, List


class JobCRUD:
    def __init__(self, sqlite: SQLiteManager) -> None:
        self.sqlite = sqlite

    def list_jobs(self, limit: int = 50) -> List[dict]:
        rows = self.sqlite.fetch_all(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT :limit",
            {"limit": limit},
        )
        return [self._normalize_job(row) for row in rows]

    def create_job(self, payload: dict) -> dict:
        self.sqlite.execute(
            """
            INSERT INTO jobs (
                id, job_type, status, progress, input_json, output_json, error_text,
                created_at, updated_at, finished_at
            ) VALUES (
                :id, :job_type, :status, :progress, :input_json, :output_json, :error_text,
                :created_at, :updated_at, :finished_at
            )
            """,
            {
                **payload,
                "input_json": dump_json(payload.get("input_json")),
                "output_json": dump_json(payload.get("output_json")),
            },
        )
        return self.get_job(payload["id"])

    def get_job(self, job_id: str) -> dict | None:
        row = self.sqlite.fetch_one("SELECT * FROM jobs WHERE id = :job_id", {"job_id": job_id})
        if not row:
            return None
        return self._normalize_job(row)

    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        output_json: dict | None = None,
        error_text: Optional[str] = None,
        updated_at: str,
        finished_at: Optional[str] = None,
    ) -> None:
        current = self.get_job(job_id)
        if not current:
            return
        self.sqlite.execute(
            """
            UPDATE jobs
            SET status = :status,
                progress = :progress,
                output_json = :output_json,
                error_text = :error_text,
                updated_at = :updated_at,
                finished_at = :finished_at
            WHERE id = :job_id
            """,
            {
                "job_id": job_id,
                "status": status if status is not None else current["status"],
                "progress": progress if progress is not None else current["progress"],
                "output_json": dump_json(output_json if output_json is not None else current["output_json"]),
                "error_text": error_text if error_text is not None else current["error_text"],
                "updated_at": updated_at,
                "finished_at": finished_at if finished_at is not None else current["finished_at"],
            },
        )

    def create_research_run(self, payload: dict) -> dict:
        self.sqlite.execute(
            """
            INSERT INTO research_runs (
                id, job_id, question, mode, plan_json, findings_json, citations_json, report_markdown, created_at
            ) VALUES (
                :id, :job_id, :question, :mode, :plan_json, :findings_json, :citations_json, :report_markdown, :created_at
            )
            """,
            {
                **payload,
                "plan_json": dump_json(payload.get("plan")),
                "findings_json": dump_json(payload.get("findings")),
                "citations_json": dump_json(payload.get("citations")),
            },
        )
        return self.get_research_run_by_job(payload["job_id"])

    def get_research_run_by_job(self, job_id: str) -> dict | None:
        row = self.sqlite.fetch_one(
            "SELECT * FROM research_runs WHERE job_id = :job_id ORDER BY created_at DESC LIMIT 1",
            {"job_id": job_id},
        )
        if not row:
            return None
        return {
            **row,
            "plan": load_json(row.get("plan_json"), []),
            "findings": load_json(row.get("findings_json"), []),
            "citations": load_json(row.get("citations_json"), []),
        }

    def _normalize_job(self, row: dict) -> dict:
        return {
            **row,
            "input_json": load_json(row.get("input_json"), {}),
            "output_json": load_json(row.get("output_json"), {}),
        }