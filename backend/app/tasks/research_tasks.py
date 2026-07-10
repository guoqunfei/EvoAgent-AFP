from __future__ import annotations


async def run_research_task(job_id: str, research_service, payload: dict) -> dict:
    return await research_service.run_job(job_id, payload)