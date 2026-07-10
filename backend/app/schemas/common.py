from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app_name: str
    env: str


class SimpleMessageResponse(BaseModel):
    success: bool = True
    message: str


class JobStatusResponse(BaseModel):
    id: str
    job_type: str
    status: str
    progress: float
    input_json: dict = Field(default_factory=dict)
    output_json: dict = Field(default_factory=dict)
    error_text: str = ""
    created_at: str
    updated_at: str
    finished_at: str = ""