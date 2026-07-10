from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class KnowledgeBaseRecord:
    id: str
    name: str
    slug: str
    description: str = ""
    root_path: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class DocumentRecord:
    id: str
    knowledge_base_id: str
    source_type: str
    source_path: str
    title: str
    checksum: str
    content: str
    metadata: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ChunkRecord:
    id: str
    document_id: str
    knowledge_base_id: str
    vector_id: int
    chunk_index: int
    text: str
    token_count: int
    metadata: dict = field(default_factory=dict)
    embedding_model: str = ""
    embedding_dim: int = 0
    created_at: str = ""


@dataclass
class ChatSessionRecord:
    id: str
    title: str
    system_prompt: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ChatMessageRecord:
    id: str
    session_id: str
    role: str
    content: str
    metadata: dict = field(default_factory=dict)
    created_at: str = ""


@dataclass
class JobRecord:
    id: str
    job_type: str
    status: str
    progress: float
    input_json: dict = field(default_factory=dict)
    output_json: dict = field(default_factory=dict)
    error_text: str = ""
    created_at: str = ""
    updated_at: str = ""
    finished_at: str = ""


@dataclass
class ResearchRunRecord:
    id: str
    job_id: str
    question: str
    mode: str
    plan: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    citations: List[dict] = field(default_factory=list)
    report_markdown: str = ""
    created_at: str = ""