from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_container, get_research_service
from app.exceptions.errors import NotFoundError
from app.schemas.common import JobStatusResponse
from typing import List


router = APIRouter()


@router.get("", response_model=List[JobStatusResponse])
def list_jobs(container=Depends(get_container)):
    rows = container.job_runner.job_crud.list_jobs()
    return [JobStatusResponse.model_validate(item) for item in rows]


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, container=Depends(get_container)):
    job = container.job_runner.job_crud.get_job(job_id)
    if not job:
        raise NotFoundError("Job not found", details={"job_id": job_id})
    return JobStatusResponse.model_validate(job)


@router.get("/{job_id}/research-report")
def get_research_report(job_id: str, service=Depends(get_research_service)):
    report = service.get_report_by_job(job_id)
    if not report:
        raise NotFoundError("Research report not found", details={"job_id": job_id})
    return report