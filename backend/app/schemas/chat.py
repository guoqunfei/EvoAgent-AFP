from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.schemas.rag import RetrievedChunk
from typing import Optional, List


class ChatSessionCreateRequest(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    system_prompt: str
    metadata: dict = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ChatMessageRequest(BaseModel):
    message: str = ""
    content: Optional[str] = None
    knowledge_base_ids: List[str] = Field(default_factory=list)
    knowledge_base_id: Optional[str] = None
    use_rag: bool = True
    top_k: Optional[int] = None
    system_prompt: Optional[str] = None
    model_key: Optional[str] = None

    @model_validator(mode="after")
    def normalize(self):
        if self.content and not self.message:
            object.__setattr__(self, "message", self.content)
        if self.knowledge_base_id:
            ids = [self.knowledge_base_id]
            for eid in self.knowledge_base_ids:
                if eid not in ids:
                    ids.append(eid)
            object.__setattr__(self, "knowledge_base_ids", ids)
        if not self.message and not self.content:
            raise ValueError("message or content is required")
        return self


class ChatMessageResponse(BaseModel):
    session_id: str
    assistant_message_id: str
    answer: str
    provider: str
    model: str
    contexts: List[RetrievedChunk] = Field(default_factory=list)


class ChatSessionDetailResponse(BaseModel):
    session: ChatSessionResponse
    messages: List[dict] = Field(default_factory=list)


class MultiModelCompareRequest(BaseModel):
    """Request for comparing responses from multiple models."""
    message: str = Field(..., description="The question or prompt to send to all models")
    model_keys: Optional[List[str]] = Field(
        default=None,
        description="List of model keys to compare. If None, uses all available models."
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional custom system prompt for all models"
    )


class ModelComparisonResult(BaseModel):
    """Result from a single model in the comparison."""
    model_key: str
    model_name: str
    provider: str
    response: str
    success: bool
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None


class MultiModelCompareResponse(BaseModel):
    """Response containing results from all compared models."""
    message: str
    results: List[ModelComparisonResult]
    total_models: int
    successful: int
    failed: int


class BatchSequenceItem(BaseModel):
    """Single AFP sequence for batch processing."""
    sequence_id: str = Field(..., description="Unique identifier for the sequence")
    sequence: str = Field(..., description="AFP amino acid sequence")
    analysis_prompt: Optional[str] = Field(
        default=None,
        description="Optional custom analysis prompt for this sequence"
    )


class BatchProcessRequest(BaseModel):
    """Request for batch processing multiple AFP sequences."""
    sequences: List[BatchSequenceItem] = Field(
        ..., 
        description="List of sequences to analyze",
        min_length=1,
        max_length=500  # Limit to prevent abuse
    )
    model_key: Optional[str] = Field(
        default=None,
        description="Model to use for analysis. If None, uses default model."
    )
    analysis_type: str = Field(
        default="comprehensive",
        description="Type of analysis: 'quick' (basic), 'comprehensive' (detailed)"
    )
    concurrent_limit: int = Field(
        default=5,
        ge=1,
        le=50,  # Increased from 20 to 50 for faster batch processing
        description="Maximum concurrent API calls (1-50)"
    )


class BatchSequenceResult(BaseModel):
    """Result for a single sequence in batch processing."""
    sequence_id: str
    sequence: str
    analysis: str
    success: bool
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    model_used: Optional[str] = None


class BatchProcessResponse(BaseModel):
    """Response containing results from batch processing."""
    batch_id: str = Field(..., description="Unique identifier for this batch job")
    status: str = Field(..., description="Status: 'completed', 'partial', 'failed'")
    total_sequences: int
    successful: int
    failed: int
    skipped: int
    results: List[BatchSequenceResult]
    total_processing_time_ms: Optional[int] = None
    created_at: str


class BatchTaskStatus(BaseModel):
    """Status information for a batch processing task."""
    batch_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: int  # 0-100 percentage
    total_sequences: int
    processed: int
    successful: int
    failed: int
    current_sequence: Optional[str] = None
    estimated_remaining_seconds: Optional[int] = None
    created_at: str
    completed_at: Optional[str] = None