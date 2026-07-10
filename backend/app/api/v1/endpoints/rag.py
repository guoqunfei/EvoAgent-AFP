from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_rag_service
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse, RetrievedChunk


router = APIRouter()


@router.post("/query", response_model=RAGQueryResponse)
def rag_query(request: RAGQueryRequest, service=Depends(get_rag_service)):
    result = service.query(
        question=request.question,
        knowledge_base_ids=request.knowledge_base_ids or None,
        top_k=request.top_k,
        system_prompt=request.system_prompt,
        use_hybrid=request.use_hybrid,
    )
    contexts = [RetrievedChunk.model_validate(item) for item in result["contexts"]]
    return RAGQueryResponse(
        answer=result["answer"],
        provider=result["provider"],
        model=result["model"],
        contexts=contexts,
        citations=result["citations"],
    )