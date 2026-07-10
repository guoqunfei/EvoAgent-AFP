# tools/afp_evaluation_tools.py
"""
AFP 突变评估工具
包含: afp_evaluate_mutation
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge import AFPSeqAnalyzer
from simulator import AFPSimulator
from .registry import tool_registry

seq_analyzer = AFPSeqAnalyzer()
simulator = AFPSimulator()


@tool_registry.tool(
    name="afp_evaluate_mutation",
    description="""评估AFP突变的结构和功能影响。多维度评估:
- 冰结合面完整性（是否破坏IBS）
- TH活性预测变化
- IRI活性预测变化
- 结构稳定性影响
- 表达可行性影响
- 安全性评估
返回: 通过/警告/拒绝 判定 + 详细评估报告""",
    original_sequence="string:原始AFP序列",
    mutated_sequence="string:突变后的AFP序列",
    mutations="string:突变描述JSON，如[{\"position\":2,\"from_aa\":\"A\",\"to_aa\":\"S\"}]",
    application_scenario="string:应用场景"
)
def handle_evaluate_mutation(original_sequence: str, mutated_sequence: str,
                             mutations: str = "[]",
                             application_scenario: str = "general") -> dict:
    """突变评估"""
    orig_seq = original_sequence.upper().strip()
    mut_seq = mutated_sequence.upper().strip()

    # 解析突变
    try:
        if isinstance(mutations, str):
            mutations_list = json.loads(mutations)
        else:
            mutations_list = mutations
    except (json.JSONDecodeError, TypeError):
        mutations_list = []

    # 分析两个序列
    orig_analysis = seq_analyzer.analyze(orig_seq)
    mut_analysis = seq_analyzer.analyze(mut_seq)

    # 模拟对比
    sim_result = simulator.compare(orig_seq, mut_seq)

    # 1. 禁区检查
    forbidden_check = {"passed": True, "issues": []}
    for pos in orig_analysis.forbidden_positions:
        if pos <= len(orig_seq) and pos <= len(mut_seq):
            if orig_seq[pos-1] != mut_seq[pos-1]:
                forbidden_check["passed"] = False
                forbidden_check["issues"].append({
                    "position": pos,
                    "original": orig_seq[pos-1],
                    "mutated": mut_seq[pos-1],
                    "severity": "REJECTED",
                    "reason": f"位置{pos}是保守功能残基，不可突变"
                })

    # 2. IBS完整性
    ibs_check = {"passed": True, "issues": []}
    for pos in orig_analysis.predicted_ibs_positions:
        if pos <= len(orig_seq) and pos <= len(mut_seq):
            if orig_seq[pos-1] != mut_seq[pos-1]:
                ibs_check["passed"] = False
                ibs_check["issues"].append({
                    "position": pos,
                    "original": orig_seq[pos-1],
                    "mutated": mut_seq[pos-1],
                    "severity": "WARNING",
                    "reason": f"IBS残基{orig_seq[pos-1]}被突变为{mut_seq[pos-1]}——可能影响冰结合"
                })

    # 3. 综合判定
    if not forbidden_check["passed"]:
        verdict = "REJECTED"
        verdict_reason = "突变命中禁区——保守功能残基不可突变"
    elif not ibs_check["passed"]:
        verdict = "WARNING"
        verdict_reason = "突变影响IBS残基——需要进一步模拟验证"
    elif sim_result["changes"]["iri_improvement_pct"] > 20:
        verdict = "PASS"
        verdict_reason = "预测显示IRI活性显著改善"
    elif sim_result["changes"]["th_change_pct"] > 10:
        verdict = "PASS"
        verdict_reason = "预测显示TH活性改善"
    elif (sim_result["changes"]["stability_change"] > 0 and
          sim_result["changes"]["expression_change"] > 0):
        verdict = "CAUTION"
        verdict_reason = "稳定性/表达改善但活性无显著变化"
    else:
        verdict = "CAUTION"
        verdict_reason = "需要更多轮设计优化"

    return {
        "success": True,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "forbidden_check": forbidden_check,
        "ibs_integrity_check": ibs_check,
        "simulation_comparison": sim_result,
        "original_analysis_summary": {
            "afp_type": orig_analysis.afp_type_prediction,
            "type_confidence": orig_analysis.type_confidence,
            "estimated_th": orig_analysis.estimated_th,
            "estimated_iri": orig_analysis.estimated_iri_ic50,
        },
        "mutated_analysis_summary": {
            "afp_type": mut_analysis.afp_type_prediction,
            "type_confidence": mut_analysis.type_confidence,
            "estimated_th": mut_analysis.estimated_th,
            "estimated_iri": mut_analysis.estimated_iri_ic50,
        },
        "recommendations": {
            "if_rejected": "请重新选择突变位点，避免保守功能残基",
            "if_warning": "建议运行冰结合模拟确认IBS影响",
            "if_passed": "可进行下一轮设计或实验验证"
        }
    }


def register_all_tools():
    """注册所有评估工具"""
    pass
