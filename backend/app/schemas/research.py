from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List


class ResearchRequest(BaseModel):
    question: str = ""
    query: Optional[str] = None
    knowledge_base_ids: List[str] = Field(default_factory=list)
    knowledge_base_id: Optional[str] = None
    mode: str = "deep"
    top_k: Optional[int] = None
    system_prompt: Optional[str] = None
    save_report: bool = True

    @model_validator(mode="after")
    def normalize(self):
        if self.query and not self.question:
            object.__setattr__(self, "question", self.query)
        if self.knowledge_base_id:
            ids = [self.knowledge_base_id]
            for eid in self.knowledge_base_ids:
                if eid not in ids:
                    ids.append(eid)
            object.__setattr__(self, "knowledge_base_ids", ids)
        if not self.question and not self.query:
            raise ValueError("question or query is required")
        return self


class ResearchRunResponse(BaseModel):
    question: str
    mode: str
    plan: List[str]
    findings: List[dict]
    citations: List[dict]
    report_markdown: str
    report_path: Optional[str] = None