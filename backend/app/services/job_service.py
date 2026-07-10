from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from app.crud.jobs import JobCRUD
from app.utils.ids import new_id
from app.utils.time import utc_now_iso
from typing import Dict


class JobRunner:
    def __init__(self, *, job_crud: JobCRUD) -> None:
        self.job_crud = job_crud
        self.tasks: Dict[str, asyncio.Task] = {}

    def submit(
        self,
        *,
        job_type: str,
        input_payload: dict,
        handler: Callable[[str], Awaitable[dict]],
    ) -> dict:
        now = utc_now_iso()
        job = self.job_crud.create_job(
            {
                "id": new_id("job"),
                "job_type": job_type,
                "status": "queued",
                "progress": 0.0,
                "input_json": input_payload,
                "output_json": {},
                "error_text": "",
                "created_at": now,
                "updated_at": now,
                "finished_at": "",
            }
        )
        task = asyncio.create_task(self._run(job["id"], handler))
        self.tasks[job["id"]] = task
        return job

    async def _run(self, job_id: str, handler: Callable[[str], Awaitable[dict]]) -> None:
        self.job_crud.update_job(job_id, status="running", progress=0.1, updated_at=utc_now_iso())
        try:
            result = await handler(job_id)
            self.job_crud.update_job(
                job_id,
                status="succeeded",
                progress=1.0,
                output_json=result,
                updated_at=utc_now_iso(),
                finished_at=utc_now_iso(),
            )
        except Exception as exc:
            self.job_crud.update_job(
                job_id,
                status="failed",
                progress=1.0,
                error_text=str(exc),
                updated_at=utc_now_iso(),
                finished_at=utc_now_iso(),
            )