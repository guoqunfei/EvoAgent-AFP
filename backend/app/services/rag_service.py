from __future__ import annotations

from collections import OrderedDict

from app.ai.core_ai.base import BaseChatProvider, BaseEmbeddingProvider, ChatMessage
from app.ai.core_ai.prompts import RAG_SYSTEM_PROMPT
from app.ai.features.rag_pipeline import build_fallback_rag_answer, format_context_block
from app.core.config import Settings
from app.crud.documents import DocumentCRUD
from app.db.vector_store import FaissVectorStore
from app.utils.text import keyword_overlap_score, tokenize
from typing import Optional, List, Dict


class RAGService:
    def __init__(
        self,
        *,
        settings: Settings,
        document_crud: DocumentCRUD,
        embedding_provider: BaseEmbeddingProvider,
        chat_provider: BaseChatProvider,
        vector_store: FaissVectorStore,
    ) -> None:
        self.settings = settings
        self.document_crud = document_crud
        self.embedding_provider = embedding_provider
        self.chat_provider = chat_provider
        self.vector_store = vector_store

    def retrieve(
        self,
        *,
        question: str,
        knowledge_base_ids: List[str] | None = None,
        top_k: Optional[int] = None,
        use_hybrid: bool = True,
    ) -> List[dict]:
        query_vector = self.embedding_provider.embed_query(question)
        vector_hits = self.vector_store.search(query_vector, top_k=self.settings.rag.fetch_k)
        score_map = {item["id"]: item["score"] for item in vector_hits}
        rows = self.document_crud.get_chunks_by_vector_ids(list(score_map.keys()))

        merged: OrderedDict[str, dict] = OrderedDict()
        for row in rows:
            if knowledge_base_ids and row["knowledge_base_id"] not in knowledge_base_ids:
                continue
            lexical = keyword_overlap_score(question, row["text"]) if use_hybrid else 0.0
            score = self.settings.rag.hybrid_alpha * score_map.get(int(row["vector_id"]), 0.0)
            score += (1.0 - self.settings.rag.hybrid_alpha) * lexical
            merged[row["id"]] = {
                "chunk_id": row["id"],
                "vector_id": int(row["vector_id"]),
                "document_id": row["document_id"],
                "knowledge_base_id": row["knowledge_base_id"],
                "title": row.get("document_title") or row["metadata"].get("title", ""),
                "source_path": row.get("source_path") or row["metadata"].get("source_path", ""),
                "score": float(score),
                "text": row["text"],
            }

        if use_hybrid:
            keyword_rows = self.document_crud.keyword_search_chunks(
                tokenize(question),
                knowledge_base_ids=knowledge_base_ids,
                limit=self.settings.rag.fetch_k,
            )
            for row in keyword_rows:
                lexical = keyword_overlap_score(question, row["text"])
                if row["id"] not in merged:
                    merged[row["id"]] = {
                        "chunk_id": row["id"],
                        "vector_id": int(row["vector_id"]),
                        "document_id": row["document_id"],
                        "knowledge_base_id": row["knowledge_base_id"],
                        "title": row.get("document_title") or row["metadata"].get("title", ""),
                        "source_path": row.get("source_path") or row["metadata"].get("source_path", ""),
                        "score": float(lexical * 0.35),
                        "text": row["text"],
                    }
                else:
                    merged[row["id"]]["score"] += lexical * 0.25

        results = sorted(merged.values(), key=lambda item: item["score"], reverse=True)
        limit = top_k or self.settings.rag.top_k
        return results[:limit]

    def query(
        self,
        *,
        question: str,
        knowledge_base_ids: List[str] | None = None,
        top_k: Optional[int] = None,
        system_prompt: Optional[str] = None,
        use_hybrid: bool = True,
    ) -> dict:
        contexts = self.retrieve(
            question=question,
            knowledge_base_ids=knowledge_base_ids,
            top_k=top_k,
            use_hybrid=use_hybrid,
        )
        answer = self.compose_answer(question=question, contexts=contexts, system_prompt=system_prompt)
        return {
            "answer": answer["text"],
            "provider": answer["provider"],
            "model": answer["model"],
            "contexts": contexts,
            "citations": [item["chunk_id"] for item in contexts],
        }

    def compose_answer(
        self,
        *,
        question: str,
        contexts: List[dict],
        system_prompt: Optional[str] = None,
    ) -> dict:
        if self.chat_provider.provider_name == "mock":
            return {
                "text": build_fallback_rag_answer(question, contexts),
                "provider": "local-fallback",
                "model": "hybrid-retrieval-template",
            }

        context_block = format_context_block(contexts, self.settings.rag.max_context_chars)
        user_message = (
            f"用户问题：{question}\n\n"
            f"可用上下文如下，请严格基于它回答：\n{context_block}"
        )
        result = self.chat_provider.generate(
            [ChatMessage(role="user", content=user_message)],
            system_prompt=system_prompt or RAG_SYSTEM_PROMPT,
            temperature=self.settings.llm.temperature,
        )
        return {"text": result.text, "provider": result.provider, "model": result.model}