from __future__ import annotations

from collections import OrderedDict
from typing import List, Dict


def heuristic_plan(question: str, max_items: int = 4) -> List[str]:
    base = [
        f"澄清问题“{question}”中的核心目标和限定条件",
        "检索本地知识库中与该问题最相关的定义、背景和上下文",
        "检索可落地的实现方案、架构模式或操作流程",
        "总结证据、不确定性以及下一步建议",
    ]
    return base[:max_items]


def unique_citations(contexts: List[dict]) -> List[dict]:
    ordered: OrderedDict[str, dict] = OrderedDict()
    for context in contexts:
        ordered.setdefault(
            context["chunk_id"],
            {
                "chunk_id": context["chunk_id"],
                "title": context["title"],
                "source_path": context["source_path"],
                "score": context["score"],
            },
        )
    return list(ordered.values())


def build_markdown_report(
    *,
    question: str,
    mode: str,
    plan: List[str],
    findings: List[dict],
    citations: List[dict],
) -> str:
    lines = [
        f"# DeepResearch Report",
        "",
        f"## 问题",
        "",
        question,
        "",
        f"## 模式",
        "",
        mode,
        "",
        "## 研究计划",
        "",
    ]
    for index, item in enumerate(plan, start=1):
        lines.append(f"{index}. {item}")
    lines.extend(["", "## 研究发现", ""])
    for index, finding in enumerate(findings, start=1):
        lines.append(f"### 发现 {index}")
        lines.append("")
        lines.append(f"- 子问题：{finding['step']}")
        lines.append(f"- 结论摘要：{finding['summary']}")
        lines.append("- 证据片段：")
        for evidence in finding.get("contexts", [])[:3]:
            lines.append(
                f"  - `{evidence['title']}` / `{evidence['source_path']}` / score={evidence['score']:.4f}"
            )
        lines.append("")
    lines.extend(["## 证据清单", ""])
    for item in citations:
        lines.append(f"- `{item['title']}` - `{item['source_path']}` - score={item['score']:.4f}")
    lines.extend(
        [
            "",
            "## 不确定性与建议",
            "",
            "- 该报告优先基于本地知识库，不代表外部互联网的最新事实。",
            "- 若知识库文档覆盖不足，DeepResearch 的结论会受到明显限制。",
            "- 建议把研究结果与原始文档、人工判断和真实实验结果结合使用。",
        ]
    )
    return "\n".join(lines)