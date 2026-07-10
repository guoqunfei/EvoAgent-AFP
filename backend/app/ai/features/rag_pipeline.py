from __future__ import annotations
from typing import List


def format_context_block(contexts: List[dict], max_chars: int) -> str:
    blocks: List[str] = []
    current_length = 0
    for index, context in enumerate(contexts, start=1):
        block = (
            f"[片段 {index}] 标题: {context['title']}\n"
            f"来源: {context['source_path']}\n"
            f"相关度: {context['score']:.4f}\n"
            f"内容: {context['text']}\n"
        )
        if current_length + len(block) > max_chars and blocks:
            break
        blocks.append(block)
        current_length += len(block)
    return "\n".join(blocks)


def build_fallback_rag_answer(question: str, contexts: List[dict]) -> str:
    if not contexts:
        return (
            f"没有在本地知识库中检索到足够支持问题“{question}”的上下文。\n\n"
            "建议你先导入 Markdown / TXT / HTML / JSON / PDF 文档，"
            "然后重新执行 RAG 查询。"
        )

    lines = [
        f"以下回答基于本地知识库检索结果，问题是：{question}",
        "",
        "检索到的重点片段：",
    ]
    for index, context in enumerate(contexts[:5], start=1):
        snippet = context["text"][:220].strip()
        lines.append(
            f"{index}. [{context['title']}] 相关度 {context['score']:.4f}，核心内容：{snippet}"
        )
    lines.extend(
        [
            "",
            "说明：当前回答来自本地模板的无模型回退模式。若要获得更自然的综合回答，可启用真实大模型提供方。",
        ]
    )
    return "\n".join(lines)