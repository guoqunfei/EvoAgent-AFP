# tools/afp_mutation_tools.py
"""
AFP 序列突变工具
包含: afp_mutate_sequence
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge import AFPSeqAnalyzer
from .registry import tool_registry

seq_analyzer = AFPSeqAnalyzer()


@tool_registry.tool(
    name="afp_mutate_sequence",
    description="""对AFP序列执行精确氨基酸突变。支持:
- 单点或多点突变（一次最多5个位点）
- 自动检查突变是否落入禁区（保守功能残基）
- 返回突变前后的序列对比和突变描述
- 预览突变前后的TH/IRI预测变化""",
    original_sequence="string:原始AFP氨基酸序列",
    mutations="string:突变列表，JSON数组格式，如[{\"position\":2,\"from_aa\":\"A\",\"to_aa\":\"S\"},{\"position\":15,\"from_aa\":\"K\",\"to_aa\":\"A\"}]，position从1开始",
    rationale="string:突变理由和设计原理说明"
)
def handle_mutate_sequence(original_sequence: str, mutations: str,
                           rationale: str = "") -> dict:
    """执行精确突变"""
    seq = original_sequence.upper().strip()

    # 解析突变列表
    try:
        if isinstance(mutations, str):
            mutations_list = json.loads(mutations)
        else:
            mutations_list = mutations
    except (json.JSONDecodeError, TypeError):
        return {"success": False, "error": f"突变列表格式错误: {mutations}"}

    if not mutations_list:
        return {"success": False, "error": "突变列表为空"}

    if len(mutations_list) > 5:
        return {"success": False, "error": "单次最多5个突变"}

    # 分析原始序列获取禁区
    analysis = seq_analyzer.analyze(seq, "mutability")
    forbidden = set(analysis.forbidden_positions)

    # 禁区检查
    warnings = []
    for mut in mutations_list:
        pos = mut.get("position", 0)
        if pos in forbidden:
            warnings.append({
                "position": pos,
                "warning": f"位置{pos}位于禁区(保守功能残基)——突变可能完全丧失活性!",
                "severity": "CRITICAL"
            })

    # 执行突变
    seq_list = list(seq)
    mutation_descriptions = []
    for mut in mutations_list:
        pos = mut.get("position", 0)
        from_aa = mut.get("from_aa", "")
        to_aa = mut.get("to_aa", "")

        if pos < 1 or pos > len(seq):
            return {"success": False, "error": f"位置{pos}超出序列长度{len(seq)}"}

        if seq_list[pos-1] != from_aa:
            return {"success": False,
                    "error": f"位置{pos}期望{from_aa}但序列中是{seq_list[pos-1]}"}

        seq_list[pos-1] = to_aa
        mutation_descriptions.append(f"{from_aa}{pos}{to_aa}")

    mutated_sequence = "".join(seq_list)

    # 分析突变后序列
    mut_analysis = seq_analyzer.analyze(mutated_sequence, "full_analysis")

    return {
        "success": True,
        "original_sequence": seq,
        "mutated_sequence": mutated_sequence,
        "mutations": mutations_list,
        "mutation_description": ", ".join(mutation_descriptions),
        "rationale": rationale,
        "warnings": warnings,
        "has_critical_warnings": len(warnings) > 0,
        "length_check": len(seq) == len(mutated_sequence),
        "preview": {
            "th_prediction_change": f"{analysis.estimated_th} → {mut_analysis.estimated_th}°C",
            "iri_prediction_change": f"{analysis.estimated_iri_ic50} → {mut_analysis.estimated_iri_ic50}µM",
        }
    }


def register_all_tools():
    """注册所有突变工具"""
    pass
