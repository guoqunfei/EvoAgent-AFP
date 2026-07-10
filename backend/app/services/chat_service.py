from __future__ import annotations

from collections.abc import Iterator

from app.ai.core_ai.base import BaseChatProvider, ChatMessage, ChatStreamChunk
from app.ai.core_ai.providers import build_model_provider
from app.ai.features.rag_pipeline import format_context_block
from app.ai.core_ai.prompts import CHAT_SYSTEM_PROMPT
from app.core.config import Settings
from app.crud.chats import ChatCRUD
from app.exceptions.errors import NotFoundError
from app.services.rag_service import RAGService
from app.utils.ids import new_id
from app.utils.time import utc_now_iso
from typing import Optional, List


class ChatService:
    def __init__(
        self,
        *,
        settings: Settings,
        chat_crud: ChatCRUD,
        rag_service: RAGService,
        chat_provider: BaseChatProvider,
    ) -> None:
        self.settings = settings
        self.chat_crud = chat_crud
        self.rag_service = rag_service
        self.chat_provider = chat_provider

    def create_session(
        self,
        *,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None,
        metadata: dict | None = None,
    ) -> dict:
        now = utc_now_iso()
        session = self.chat_crud.create_session(
            {
                "id": new_id("chat"),
                "title": title or "New Chat Session",
                "system_prompt": system_prompt or CHAT_SYSTEM_PROMPT,
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now,
            }
        )
        return session

    def list_sessions(self) -> List[dict]:
        return self.chat_crud.list_sessions()

    def get_session_detail(self, session_id: str) -> dict:
        session = self.chat_crud.get_session(session_id)
        if not session:
            raise NotFoundError("Chat session not found", details={"session_id": session_id})
        messages = self.chat_crud.list_messages(session_id)
        return {"session": session, "messages": messages}

    def send_message(
        self,
        *,
        session_id: str,
        message: str,
        knowledge_base_ids: List[str] | None = None,
        use_rag: bool = True,
        top_k: Optional[int] = None,
        system_prompt: Optional[str] = None,
        model_key: Optional[str] = None,
    ) -> dict:
        session = self.chat_crud.get_session(session_id)
        if not session:
            raise NotFoundError("Chat session not found", details={"session_id": session_id})

        now = utc_now_iso()
        user_record = self.chat_crud.add_message(
            {
                "id": new_id("msg"),
                "session_id": session_id,
                "role": "user",
                "content": message,
                "metadata": {"knowledge_base_ids": knowledge_base_ids or [], "use_rag": use_rag},
                "created_at": now,
            }
        )

        contexts: List[dict] = []
        answer_text = ""
        provider = "local-fallback"
        model = "chat-template"

        if use_rag:
            contexts = self.rag_service.retrieve(
                question=message,
                knowledge_base_ids=knowledge_base_ids,
                top_k=top_k,
            )

        if self.chat_provider.provider_name == "mock":
            if use_rag:
                composed = self.rag_service.compose_answer(question=message, contexts=contexts)
                answer_text = composed["text"]
                provider = composed["provider"]
                model = composed["model"]
            else:
                answer_text = (
                    "当前使用的是 Mock Chat Provider。\n\n"
                    f"你输入的内容是：{message}\n\n"
                    "你可以打开 `LLM__ENABLED=true` 并配置 OpenAI 兼容模型，"
                    "让这里切换为真实大模型对话。"
                )
        else:
            # Select provider based on model_key if specified
            if model_key:
                selected_provider = build_model_provider(self.settings, model_key)
            else:
                selected_provider = self.chat_provider
            
            history = self.chat_crud.list_messages(session_id)
            messages = [ChatMessage(role=item["role"], content=item["content"]) for item in history]
            if use_rag and contexts:
                context_block = format_context_block(contexts, self.settings.rag.max_context_chars)
                messages.append(ChatMessage(role="system", content=f"检索上下文：\n{context_block}"))
            result = selected_provider.generate(
                messages,
                system_prompt=system_prompt or session["system_prompt"],
                temperature=self.settings.llm.temperature,
            )
            answer_text = result.text
            provider_name = result.provider
            model = result.model

        assistant_record = self.chat_crud.add_message(
            {
                "id": new_id("msg"),
                "session_id": session_id,
                "role": "assistant",
                "content": answer_text,
                "metadata": {"provider": provider_name, "model": model, "reply_to": user_record["id"], "model_key": model_key},
                "created_at": utc_now_iso(),
            }
        )

        title = session["title"]
        if title == "New Chat Session":
            title = message[:40].strip() or title
        self.chat_crud.touch_session(session_id, updated_at=utc_now_iso(), title=title)

        return {
            "session_id": session_id,
            "assistant_message_id": assistant_record["id"],
            "answer": answer_text,
            "provider": provider,
            "model": model,
            "contexts": contexts,
        }

    def send_message_stream(
        self,
        *,
        session_id: str,
        message: str,
        system_prompt: Optional[str] = None,
        model_key: Optional[str] = None,
    ) -> Iterator[ChatStreamChunk]:
        """Stream chat response chunks from the LLM provider.
        Uses the specified model_key (from CHAT_MODELS config) or falls back to default."""
        session = self.chat_crud.get_session(session_id)
        if not session:
            raise NotFoundError("Chat session not found", details={"session_id": session_id})

        now = utc_now_iso()
        self.chat_crud.add_message({
            "id": new_id("msg"),
            "session_id": session_id,
            "role": "user",
            "content": message,
            "metadata": {"use_rag": False, "model_key": model_key},
            "created_at": now,
        })

        history = self.chat_crud.list_messages(session_id)
        messages = [ChatMessage(role=item["role"], content=item["content"]) for item in history]

        # Select provider based on model choice
        provider = build_model_provider(self.settings, model_key)

        full_text = ""
        for chunk in provider.generate_stream(
            messages,
            system_prompt=system_prompt or session["system_prompt"],
            temperature=self.settings.llm.temperature,
        ):
            full_text += chunk.content
            yield chunk

        # Persist assistant message
        self.chat_crud.add_message({
            "id": new_id("msg"),
            "session_id": session_id,
            "role": "assistant",
            "content": full_text,
            "metadata": {"provider": self.chat_provider.provider_name, "model": self.chat_provider.model_name},
            "created_at": utc_now_iso(),
        })

        title = session["title"]
        if title == "New Chat Session":
            title = message[:40].strip() or title
        self.chat_crud.touch_session(session_id, updated_at=utc_now_iso(), title=title)

    def compare_models(
        self,
        *,
        message: str,
        model_keys: List[str] | None = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Compare responses from multiple models for the same message.
        Returns results from all specified models (or all available if not specified).
        """
        import time
        from app.ai.core_ai.providers import list_available_models
        
        # Get all available models if not specified
        if not model_keys:
            available = list_available_models(self.settings)
            model_keys = [m["id"] for m in available]
        
        results = []
        successful = 0
        failed = 0
        
        for model_key in model_keys:
            try:
                start_time = time.time()
                
                # Build provider for this model
                provider = build_model_provider(self.settings, model_key)
                
                # Create a simple message for comparison
                messages = [ChatMessage(role="user", content=message)]
                
                # Generate response
                result = provider.generate(
                    messages,
                    system_prompt=system_prompt,
                    temperature=self.settings.llm.temperature,
                )
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                results.append({
                    "model_key": model_key,
                    "model_name": provider.model_name,
                    "provider": provider.provider_name,
                    "response": result.text,
                    "success": True,
                    "error_message": None,
                    "latency_ms": latency_ms,
                })
                successful += 1
                
            except Exception as e:
                results.append({
                    "model_key": model_key,
                    "model_name": "",
                    "provider": "",
                    "response": "",
                    "success": False,
                    "error_message": str(e),
                    "latency_ms": None,
                })
                failed += 1
        
        return {
            "message": message,
            "results": results,
            "total_models": len(model_keys),
            "successful": successful,
            "failed": failed,
        }

    async def process_batch_sequences(
        self,
        *,
        sequences: List[dict],
        model_key: Optional[str] = None,
        analysis_type: str = "comprehensive",
        concurrent_limit: int = 5,
    ) -> dict:
        """
        Process multiple AFP sequences concurrently.
        Returns batch_id and starts background processing.
        """
        import asyncio
        import time
        from app.utils.ids import new_id
        from app.utils.time import utc_now_iso
        
        batch_id = new_id("batch")
        created_at = utc_now_iso()
        
        # Initialize batch status in memory (in production, use Redis/database)
        batch_status = {
            "batch_id": batch_id,
            "status": "processing",
            "progress": 0,
            "total_sequences": len(sequences),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "current_sequence": None,
            "created_at": created_at,
            "completed_at": None,
            "results": [],
        }
        
        # Store in service instance for status tracking
        if not hasattr(self, '_batch_tasks'):
            self._batch_tasks = {}
        self._batch_tasks[batch_id] = batch_status
        
        # Process sequences with concurrency limit
        semaphore = asyncio.Semaphore(concurrent_limit)
        start_time = time.time()
        
        async def process_single(seq_item: dict) -> dict:
            async with semaphore:
                seq_id = seq_item.get("sequence_id", "unknown")
                sequence = seq_item.get("sequence", "")
                prompt = seq_item.get("analysis_prompt")
                
                batch_status["current_sequence"] = seq_id
                
                try:
                    proc_start = time.time()
                    
                    # Build provider
                    provider = build_model_provider(self.settings, model_key) if model_key else self.chat_provider
                    
                    # Create analysis prompt
                    if not prompt:
                        if analysis_type == "quick":
                            # 快速分析模式 - 只提取关键信息,减少生成内容
                            prompt = f"""请简要分析以下AFP蛋白序列的关键特征：

序列: {sequence}

要求（简洁输出，每项1-2句话）：
1. 序列长度和主要氨基酸组成
2. 是否有明显的重复模式
3. 预测活性等级（高/中/低）
4. 一句话总结

保持回答简洁。"""
                        else:
                            # 全面分析模式
                            prompt = f"""请全面分析以下抗冻蛋白(AFP)序列：

序列: {sequence}

请从以下角度进行分析：
1. 序列特征（长度、氨基酸组成）
2. 可能的冰结合位点
3. 活性预测
4. 结构特性推测
5. 潜在应用场景

请给出专业、详细的分析报告。"""
                    
                    # Call LLM
                    messages = [
                        ChatMessage(role="system", content="你是一位专业的抗冻蛋白分析专家。"),
                        ChatMessage(role="user", content=prompt),
                    ]
                    
                    result = provider.generate(
                        messages,
                        temperature=self.settings.llm.temperature,
                    )
                    
                    proc_time = int((time.time() - proc_start) * 1000)
                    
                    batch_status["successful"] += 1
                    
                    return {
                        "sequence_id": seq_id,
                        "sequence": sequence,
                        "analysis": result.text,
                        "success": True,
                        "error_message": None,
                        "processing_time_ms": proc_time,
                        "model_used": result.model or provider.model_name,
                    }
                    
                except Exception as e:
                    batch_status["failed"] += 1
                    return {
                        "sequence_id": seq_id,
                        "sequence": sequence,
                        "analysis": "",
                        "success": False,
                        "error_message": str(e),
                        "processing_time_ms": None,
                        "model_used": None,
                    }
                finally:
                    batch_status["processed"] += 1
                    batch_status["progress"] = int(
                        (batch_status["processed"] / batch_status["total_sequences"]) * 100
                    )
        
        # Run all tasks with concurrency control
        tasks = [process_single(seq) for seq in sequences]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in gather
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append({
                    "sequence_id": sequences[i].get("sequence_id", "unknown"),
                    "sequence": sequences[i].get("sequence", ""),
                    "analysis": "",
                    "success": False,
                    "error_message": f"Task error: {str(result)}",
                    "processing_time_ms": None,
                    "model_used": None,
                })
                batch_status["failed"] += 1
            else:
                final_results.append(result)
        
        total_time = int((time.time() - start_time) * 1000)
        
        # Update final status
        batch_status["status"] = "completed" if batch_status["failed"] == 0 else "partial"
        batch_status["completed_at"] = utc_now_iso()
        batch_status["results"] = final_results
        batch_status["total_processing_time_ms"] = total_time
        batch_status["current_sequence"] = None
        
        return {
            "batch_id": batch_id,
            "status": batch_status["status"],
            "total_sequences": len(sequences),
            "successful": batch_status["successful"],
            "failed": batch_status["failed"],
            "skipped": 0,
            "results": final_results,
            "total_processing_time_ms": total_time,
            "created_at": created_at,
        }
    
    def get_batch_status(self, batch_id: str) -> dict:
        """Get status of a batch processing task."""
        if not hasattr(self, '_batch_tasks'):
            self._batch_tasks = {}
        
        if batch_id not in self._batch_tasks:
            raise NotFoundError("Batch task not found", details={"batch_id": batch_id})
        
        status = self._batch_tasks[batch_id]
        
        # Calculate estimated remaining time
        if status["status"] == "processing" and status["processed"] > 0:
            elapsed = (utc_now_iso() - status["created_at"]).total_seconds() if hasattr(status["created_at"], 'total_seconds') else 60
            avg_per_seq = elapsed / max(status["processed"], 1)
            remaining = avg_per_seq * (status["total_sequences"] - status["processed"])
            status["estimated_remaining_seconds"] = int(remaining)
        
        return {
            "batch_id": status["batch_id"],
            "status": status["status"],
            "progress": status["progress"],
            "total_sequences": status["total_sequences"],
            "processed": status["processed"],
            "successful": status["successful"],
            "failed": status["failed"],
            "current_sequence": status["current_sequence"],
            "estimated_remaining_seconds": status.get("estimated_remaining_seconds"),
            "created_at": status["created_at"],
            "completed_at": status["completed_at"],
        }
