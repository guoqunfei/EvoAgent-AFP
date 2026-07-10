from __future__ import annotations

import asyncio
from pathlib import Path

from app.ai.core_ai.base import BaseChatProvider, ChatMessage
from app.ai.core_ai.prompts import RESEARCH_PLANNER_PROMPT, RESEARCH_SYNTHESIS_PROMPT
from app.ai.features.deep_research import build_markdown_report, heuristic_plan, unique_citations
from app.core.config import Settings
from app.crud.documents import DocumentCRUD
from app.crud.jobs import JobCRUD
from app.services.rag_service import RAGService
from app.utils.ids import new_id
from app.utils.time import utc_now_iso
from typing import List


class ResearchService:
    def __init__(
        self,
        *,
        settings: Settings,
        document_crud: DocumentCRUD,
        rag_service: RAGService,
        chat_provider: BaseChatProvider,
        job_crud: JobCRUD,
    ) -> None:
        self.settings = settings
        self.document_crud = document_crud
        self.rag_service = rag_service
        self.chat_provider = chat_provider
        self.job_crud = job_crud

    async def run_job(self, job_id: str, payload: dict) -> dict:
        return await asyncio.to_thread(self.run_sync, job_id=job_id, payload=payload)

    def run_sync(self, *, job_id: str, payload: dict) -> dict:
        question = payload["question"]
        knowledge_base_ids = payload.get("knowledge_base_ids") or []
        mode = payload.get("mode") or self.settings.research.default_mode
        top_k = payload.get("top_k") or self.settings.rag.top_k
        save_report = bool(payload.get("save_report", True))

        plan = self._build_plan(question)
        findings: List[dict] = []
        all_contexts: List[dict] = []

        for step in plan[: self.settings.research.max_rounds]:
            contexts = self.rag_service.retrieve(
                question=step,
                knowledge_base_ids=knowledge_base_ids,
                top_k=top_k,
            )
            summary = self._summarize_step(step, contexts)
            findings.append({"step": step, "summary": summary, "contexts": contexts[:3]})
            all_contexts.extend(contexts[: self.settings.research.max_queries_per_round])

        citations = unique_citations(all_contexts[: self.settings.research.max_final_contexts])
        report_markdown = self._compose_report(
            question=question,
            mode=mode,
            plan=plan,
            findings=findings,
            citations=citations,
        )
        report_path = self._save_report(job_id, report_markdown) if save_report else None

        if self.job_crud.get_job(job_id):
            self.job_crud.create_research_run(
                {
                    "id": new_id("research"),
                    "job_id": job_id,
                    "question": question,
                    "mode": mode,
                    "plan": plan,
                    "findings": findings,
                    "citations": citations,
                    "report_markdown": report_markdown,
                    "created_at": utc_now_iso(),
                }
            )
        return {
            "question": question,
            "mode": mode,
            "plan": plan,
            "findings": findings,
            "citations": citations,
            "report_markdown": report_markdown,
            "report_path": report_path,
        }

    def get_report_by_job(self, job_id: str) -> dict | None:
        return self.job_crud.get_research_run_by_job(job_id)

    def _build_plan(self, question: str) -> List[str]:
        if self.chat_provider.provider_name == "mock":
            return heuristic_plan(question, max_items=min(4, self.settings.research.max_rounds + 1))

        result = self.chat_provider.generate(
            [ChatMessage(role="user", content=question)],
            system_prompt=RESEARCH_PLANNER_PROMPT,
            temperature=0.1,
        )
        lines = [line.strip(" -0123456789.") for line in result.text.splitlines() if line.strip()]
        return lines[:5] if lines else heuristic_plan(question)

    def _summarize_step(self, step: str, contexts: List[dict]) -> str:
        if not contexts:
            return "本地知识库中没有检索到足够支持该子问题的上下文。"
        if self.chat_provider.provider_name == "mock":
            top = contexts[0]
            return f"最相关证据来自《{top['title']}》，主要涉及：{top['text'][:180]}。"
        prompt = (
            f"子问题：{step}\n\n"
            "请根据以下上下文给出简短结论：\n"
            + "\n\n".join(f"- {ctx['title']}: {ctx['text'][:500]}" for ctx in contexts[:3])
        )
        result = self.chat_provider.generate(
            [ChatMessage(role="user", content=prompt)],
            system_prompt="请输出 2 到 4 句简洁结论，并保留不确定性说明。",
            temperature=0.1,
        )
        return result.text

    def _compose_report(
        self,
        *,
        question: str,
        mode: str,
        plan: List[str],
        findings: List[dict],
        citations: List[dict],
    ) -> str:
        if self.chat_provider.provider_name == "mock":
            return build_markdown_report(
                question=question,
                mode=mode,
                plan=plan,
                findings=findings,
                citations=citations,
            )

        synthesis_input = (
            f"问题：{question}\n\n"
            f"计划：{plan}\n\n"
            f"发现：{findings}\n\n"
            f"引用：{citations}"
        )
        result = self.chat_provider.generate(
            [ChatMessage(role="user", content=synthesis_input)],
            system_prompt=RESEARCH_SYNTHESIS_PROMPT,
            temperature=0.2,
        )
        return result.text

    def _save_report(self, job_id: str, report_markdown: str) -> str:
        report_dir = self.settings.resolve_backend_path(self.settings.research.save_reports_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        path = Path(report_dir) / f"{job_id}.md"
        path.write_text(report_markdown, encoding="utf-8")
        return str(path)