from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_job_runner, get_research_service
from app.schemas.common import JobStatusResponse
from app.schemas.research import ResearchRequest, ResearchRunResponse
from app.utils.ids import new_id


router = APIRouter()


@router.post("/run", response_model=ResearchRunResponse)
def run_research(request: ResearchRequest, service=Depends(get_research_service)):
    result = service.run_sync(
        job_id=new_id("preview"),
        payload=request.model_dump(exclude={"query", "knowledge_base_id"}),
    )
    return ResearchRunResponse.model_validate(result)


@router.post("/jobs", response_model=JobStatusResponse)
def create_research_job(
    request: ResearchRequest,
    runner=Depends(get_job_runner),
    service=Depends(get_research_service),
):
    payload = request.model_dump(exclude={"query", "knowledge_base_id"})
    job = runner.submit(
        job_type="deep_research",
        input_payload=payload,
        handler=lambda job_id: service.run_job(job_id, payload),
    )
    return JobStatusResponse.model_validate(job)