from __future__ import annotations

from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.core_ai.embeddings import build_embedding_provider
from app.ai.core_ai.providers import build_chat_provider
from app.api.v1.router import api_router
from app.core.config import BACKEND_DIR, get_settings
from app.core.logging import configure_logging
from app.core.registry import AppContainer
from app.crud.chats import ChatCRUD
from app.crud.documents import DocumentCRUD
from app.crud.jobs import JobCRUD
from app.db.sqlite import SQLiteManager
from app.db.vector_store import FaissVectorStore
from app.exceptions.handlers import register_exception_handlers
from app.middlewares.request_context import RequestContextMiddleware
from app.middlewares.timing import TimingMiddleware
from app.services.chat_service import ChatService
from app.services.job_service import JobRunner
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.rag_service import RAGService
from app.services.research_service import ResearchService
from app.services.afp_service import AFPAgentService


logger = getLogger(__name__)


def _build_container() -> AppContainer:
    settings = get_settings()
    configure_logging(settings.app.debug)

    # 初始化基础设施组件
    sqlite = SQLiteManager(
        db_path=settings.resolve_backend_path(settings.sqlite.db_path),
        schema_path=BACKEND_DIR / "sql" / "init_schema.sql",
        wal_mode=settings.sqlite.wal_mode,
    )
    sqlite.initialize()

    vector_store = FaissVectorStore(
        dimension=settings.embedding.dimension,
        index_path=settings.resolve_backend_path(settings.vector.index_path),
        meta_path=settings.resolve_backend_path(settings.vector.meta_path),
        metric=settings.vector.metric,
    )
    vector_store.load()

    embedding_provider = build_embedding_provider(settings)
    chat_provider = build_chat_provider(settings)

    # 组装容器
    container = AppContainer(
        settings=settings,
        sqlite=sqlite,
        vector_store=vector_store,
        embedding_provider=embedding_provider,
        chat_provider=chat_provider,
    )

    # 创建 CRUD 层
    document_crud = DocumentCRUD(sqlite)
    chat_crud = ChatCRUD(sqlite)
    job_crud = JobCRUD(sqlite)

    # 创建服务层并注入依赖
    container.knowledge_base_service = KnowledgeBaseService(
        settings=settings,
        document_crud=document_crud,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )
    container.rag_service = RAGService(
        settings=settings,
        document_crud=document_crud,
        embedding_provider=embedding_provider,
        chat_provider=chat_provider,
        vector_store=vector_store,
    )
    container.chat_service = ChatService(
        settings=settings,
        chat_crud=chat_crud,
        rag_service=container.rag_service,
        chat_provider=chat_provider,
    )
    container.research_service = ResearchService(
        settings=settings,
        document_crud=document_crud,
        rag_service=container.rag_service,
        chat_provider=chat_provider,
        job_crud=job_crud,
    )
    container.job_runner = JobRunner(job_crud=job_crud)

    # 创建 AFPAgent 服务
    container.afp_service = AFPAgentService(settings=settings)

    return container


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 启动阶段 ---
    container = _build_container()
    app.state.container = container
    logger.info("Application initialized.")
    try:
        yield
    finally:
        # --- 关闭阶段 ---
        container.vector_store.persist()
        logger.info("Application shutdown completed.")


def create_application() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        debug=settings.app.debug,
        lifespan=lifespan,
    )

    # 注册中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(TimingMiddleware)

    # 注册全局异常处理器
    register_exception_handlers(app)

    # 挂载 v1 版本路由
    app.include_router(api_router, prefix=settings.app.api_prefix)

    return app