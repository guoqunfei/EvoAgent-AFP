from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.ai.core_ai.providers import list_available_models
from app.api.deps import get_chat_service
from app.core.config import get_settings
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    MultiModelCompareRequest,
    MultiModelCompareResponse,
    BatchProcessRequest,
    BatchProcessResponse,
    BatchTaskStatus,
)
from app.schemas.rag import RetrievedChunk


router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse)
def create_session(request: ChatSessionCreateRequest, service=Depends(get_chat_service)):
    return ChatSessionResponse.model_validate(service.create_session(**request.model_dump()))


@router.get("/sessions", response_model=List[ChatSessionResponse])
def list_sessions(service=Depends(get_chat_service)):
    return [ChatSessionResponse.model_validate(item) for item in service.list_sessions()]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
def get_session(session_id: str, service=Depends(get_chat_service)):
    detail = service.get_session_detail(session_id)
    return ChatSessionDetailResponse(
        session=ChatSessionResponse.model_validate(detail["session"]),
        messages=detail["messages"],
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
def send_message(session_id: str, request: ChatMessageRequest, service=Depends(get_chat_service)):
    result = service.send_message(
        session_id=session_id,
        message=request.message,
        knowledge_base_ids=request.knowledge_base_ids or None,
        use_rag=request.use_rag,
        top_k=request.top_k,
        system_prompt=request.system_prompt,
        model_key=request.model_key,
    )
    return ChatMessageResponse(
        session_id=result["session_id"],
        assistant_message_id=result["assistant_message_id"],
        answer=result["answer"],
        provider=result["provider"],
        model=result["model"],
        contexts=[RetrievedChunk.model_validate(item) for item in result["contexts"]],
    )


@router.get("/models")
def list_models():
    """Return available chat models for the frontend model switcher."""
    return {"models": list_available_models(get_settings()), "default": get_settings().chat_models.default}


@router.post("/sessions/{session_id}/messages/stream")
def send_message_stream(session_id: str, request: ChatMessageRequest, service=Depends(get_chat_service)):
    """SSE streaming chat endpoint — yields chunks as they arrive from the LLM."""

    def _event_stream():
        try:
            for chunk in service.send_message_stream(
                session_id=session_id,
                message=request.message,
                system_prompt=request.system_prompt,
                model_key=request.model_key,
            ):
                if chunk.content:
                    yield f"data: {_sse_json({'type': 'chunk', 'content': chunk.content})}\n\n"
                if chunk.finish_reason:
                    yield f"data: {_sse_json({'type': 'done', 'finish_reason': chunk.finish_reason})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {_sse_json({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_json(data: dict) -> str:
    import json
    return json.dumps(data, ensure_ascii=False)


@router.post("/compare-models", response_model=MultiModelCompareResponse)
def compare_models(request: MultiModelCompareRequest, service=Depends(get_chat_service)):
    """
    Compare responses from multiple models for the same message.
    Useful for evaluating different models' performance on AFP protein analysis tasks.
    """
    result = service.compare_models(
        message=request.message,
        model_keys=request.model_keys,
        system_prompt=request.system_prompt,
    )
    return MultiModelCompareResponse(**result)


@router.post("/batch/process", response_model=BatchProcessResponse)
async def batch_process_sequences(request: BatchProcessRequest, service=Depends(get_chat_service)):
    """
    Process multiple AFP sequences concurrently using AI models.
    Supports up to 500 sequences with configurable concurrency.
    """
    # Convert Pydantic models to dicts for service layer
    sequences = [seq.model_dump() for seq in request.sequences]
    
    result = await service.process_batch_sequences(
        sequences=sequences,
        model_key=request.model_key,
        analysis_type=request.analysis_type,
        concurrent_limit=request.concurrent_limit,
    )
    
    return BatchProcessResponse(**result)


@router.get("/batch/{batch_id}/status", response_model=BatchTaskStatus)
def get_batch_status(batch_id: str, service=Depends(get_chat_service)):
    """
    Get status of a batch processing task.
    Returns progress percentage and estimated completion time.
    """
    status = service.get_batch_status(batch_id)
    return BatchTaskStatus(**status)


@router.get("/batch/{batch_id}/export")
def export_batch_results(batch_id: str, format: str = "csv", service=Depends(get_chat_service)):
    """
    Export batch processing results as CSV or JSON.
    Format: 'csv' or 'json'
    """
    from fastapi.responses import Response
    import json
    import csv
    import io
    
    status = service.get_batch_status(batch_id)
    if status["status"] not in ["completed", "partial"]:
        raise HTTPException(status_code=400, detail="Batch processing not completed yet")
    
    # Get full results from service
    if not hasattr(service, '_batch_tasks') or batch_id not in service._batch_tasks:
        raise HTTPException(status_code=404, detail="Batch task not found")
    
    results = service._batch_tasks[batch_id]["results"]
    
    if format == "json":
        json_str = json.dumps(results, ensure_ascii=False, indent=2)
        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=batch_{batch_id}.json"}
        )
    elif format == "csv":
        output = io.StringIO()
        if results:
            writer = csv.DictWriter(output, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=batch_{batch_id}.csv"}
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'csv' or 'json'")