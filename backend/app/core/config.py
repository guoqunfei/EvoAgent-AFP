from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional, List, Dict, Any

# Python 3.8 compatibility for type hints
if sys.version_info < (3, 9):
    from typing import List as list
    from typing import Dict as dict

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录（backend 目录），用于定位默认环境变量文件及相对路径解析
APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = BACKEND_DIR / ".env.development"



class AppSettings(BaseModel):
    """应用全局配置，名称、环境、调试模式、API前缀及跨域白名单"""

    name: str = "Bio Backend"
    env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])



class SQLiteSettings(BaseModel):
    """SQLite 数据库配置，连接路径及是否启用 WAL 模式"""

    db_path: str = "app/local_data/sqlite/backend.db"
    wal_mode: bool = True



class VectorSettings(BaseModel):
    provider: str = "faiss"
    index_path: str = "app/local_data/faiss/main.index"
    meta_path: str = "app/local_data/faiss/main.meta.json"
    metric: str = "cosine"


class EmbeddingSettings(BaseModel):
    provider: str = "hash"
    model: str = "local-hash-embedding"
    dimension: int = 384
    batch_size: int = 32
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout_seconds: int = 60


class LLMSettings(BaseModel):
    enabled: bool = False
    provider: str = "mock"
    model: str = "demo-chat-model"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.2
    timeout_seconds: int = 120


class ModelItem(BaseModel):
    """Configuration for a single chat model."""
    provider: str = "openai-compatible"
    model: str = ""
    base_url: str = ""
    api_key: str = ""


class ChatModelsConfig(BaseModel):
    """Multi-model configuration — maps display names to provider configs."""
    default: str = "deepseek"
    models: Dict[str, ModelItem] = {}


class RAGSettings(BaseModel):
    top_k: int = 6
    fetch_k: int = 18
    max_context_chars: int = 12000
    hybrid_alpha: float = 0.75
    chunk_size: int = 1000
    chunk_overlap: int = 180


class ResearchSettings(BaseModel):
    default_mode: str = "deep"
    max_rounds: int = 3
    max_queries_per_round: int = 3
    max_final_contexts: int = 12
    save_reports_dir: str = "app/local_data/exports/research"


class KnowledgeBaseSettings(BaseModel):
    root_dir: str = "app/local_data/knowledge_base"
    uploads_dir: str = "app/local_data/uploads"
    allowed_suffixes: List[str] = Field(
        default_factory=lambda: [".md", ".txt", ".html", ".json", ".pdf"]
    )


class AFPAgentSettings(BaseModel):
    """AFPAgent 抗冻蛋白智能设计配置"""
    llm_model: str = "gpt-4o"
    llm_provider: str = "openai"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096
    max_iterations: int = 20
    auto_generate_skills: bool = True
    min_experiments_for_skill: int = 3
    data_dir: str = "app/local_data/afp_agent/data"
    skills_dir: str = "app/local_data/afp_agent/skills"
    save_reports_dir: str = "app/local_data/exports/afp_reports"


class Settings(BaseSettings):
    """全局配置聚合类，从.env文件加载并支持嵌套分隔符解析"""

    app: AppSettings = AppSettings()
    sqlite: SQLiteSettings = SQLiteSettings()

    vector: VectorSettings = VectorSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    llm: LLMSettings = LLMSettings()
    chat_models: ChatModelsConfig = ChatModelsConfig()
    rag: RAGSettings = RAGSettings()
    research: ResearchSettings = ResearchSettings()
    knowledge_base: KnowledgeBaseSettings = KnowledgeBaseSettings()
    afp_agent: AFPAgentSettings = AFPAgentSettings()

    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",   # 如 APP__NAME 可映射到 Settings.app.name
        extra="ignore",              # 忽略未定义的环境变量，避免启动报错
    )

    def resolve_backend_path(self, raw_path: str) -> Path:
        """将相对路径转换为基于 BACKEND_DIR 的绝对路径（已绝对则直接返回）"""
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return BACKEND_DIR / raw_path

    def ensure_directories(self) -> None:
        """确保配置中用到的本地目录存在（如数据库文件所在文件夹）"""
        directories = [
            self.resolve_backend_path(self.sqlite.db_path).parent,
            self.resolve_backend_path(self.vector.index_path).parent,
            self.resolve_backend_path(self.vector.meta_path).parent,
            self.resolve_backend_path(self.knowledge_base.root_dir),
            self.resolve_backend_path(self.knowledge_base.uploads_dir),
            self.resolve_backend_path(self.research.save_reports_dir),
            self.resolve_backend_path(self.afp_agent.data_dir),
            self.resolve_backend_path(self.afp_agent.skills_dir),
            self.resolve_backend_path(self.afp_agent.save_reports_dir),
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    

    def public_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        if data["llm"].get("api_key"):
            data["llm"]["api_key"] = "***"
        if data["embedding"].get("api_key"):
            data["embedding"]["api_key"] = "***"
        if data.get("afp_agent", {}).get("llm_api_key"):
            data["afp_agent"]["llm_api_key"] = "***"
        return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    单例获取全局配置实例（缓存仅创建一次），
    并在首次创建时自动创建必要的本地目录
    """
    settings = Settings()
    settings.ensure_directories()
    return settings
