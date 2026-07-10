from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(container=Depends(get_container)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=container.settings.app.name,
        env=container.settings.app.env,
    )


@router.get("/runtime-config")
def runtime_config(container=Depends(get_container)) -> dict:
    return container.settings.public_dict()
