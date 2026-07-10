from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.db.sqlite import SQLiteManager
from app.ai.core_ai.base import BaseChatProvider, BaseEmbeddingProvider
from app.db.vector_store import FaissVectorStore

@dataclass
class AppContainer:
    settings: Settings
    sqlite: SQLiteManager
    vector_store: FaissVectorStore
    embedding_provider: BaseEmbeddingProvider
    chat_provider: BaseChatProvider
    knowledge_base_service: object | None = None
    rag_service: object | None = None
    chat_service: object | None = None
    research_service: object | None = None
    afp_service: object | None = None
    job_runner: object | None = None
