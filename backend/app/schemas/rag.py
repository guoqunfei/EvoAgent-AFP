from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List


class RAGQueryRequest(BaseModel):
    question: str = ""
    query: Optional[str] = None
    knowledge_base_ids: List[str] = Field(default_factory=list)
    knowledge_base_id: Optional[str] = None
    top_k: Optional[int] = None
    system_prompt: Optional[str] = None
    use_hybrid: bool = True

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
        return self


class RetrievedChunk(BaseModel):
    chunk_id: str
    vector_id: int
    document_id: str
    knowledge_base_id: str
    title: str
    source_path: str
    score: float
    text: str


class RAGQueryResponse(BaseModel):
    answer: str
    provider: str
    model: str
    contexts: List[RetrievedChunk]
    citations: List[str] = Field(default_factory=list)