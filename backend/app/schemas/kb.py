from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List


class KnowledgeBaseCreateRequest(BaseModel):
    name: str
    slug: Optional[str] = None
    description: str = ""
    root_path: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    root_path: str
    metadata: dict = Field(default_factory=dict)
    document_count: int = 0
    chunk_count: int = 0
    created_at: str
    updated_at: str


class IngestPathRequest(BaseModel):
    path: str
    recursive: bool = True
    source_type: str = "local_file"


class IngestTextRequest(BaseModel):
    title: str
    text: str
    source_path: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class IngestResponse(BaseModel):
    knowledge_base_id: str
    files_seen: int
    documents_written: int
    chunks_written: int
    errors: List[str] = Field(default_factory=list)


class IngestUploadResponse(BaseModel):
    knowledge_base_id: str
    document_id: str
    title: str
    source_type: str
    chunk_count: int
    checksum: str


class DocumentResponse(BaseModel):
    id: str
    knowledge_base_id: str
    source_type: str
    source_path: str
    title: str
    checksum: str
    metadata: dict = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    knowledge_base_id: str
    vector_id: int
    chunk_index: int
    text: str
    token_count: int
    metadata: dict = Field(default_factory=dict)
    document_title: Optional[str] = None
    source_path: Optional[str] = None