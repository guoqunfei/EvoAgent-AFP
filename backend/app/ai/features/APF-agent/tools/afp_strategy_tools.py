# tools/afp_strategy_tools.py
"""
AFP 设计策略 + 结果总结工具
包含: afp_design_strategy, afp_design_summary
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge import AFPSeqAnalyzer, AFPLiteratureKnowledge
from .registry import tool_registry

seq_analyzer = AFPSeqAnalyzer()
literature = AFPLiteratureKnowledge()


# ============================================================
# 工具1: afp_design_strategy —— 设计策略推荐
# ============================================================
@tool_registry.tool(
    name="afp_design_strategy",
    description="""基于当前设计状态和知识库，生成推荐的后续设计策略。包括:
- 基于知识库的禁区规避建议
- 基于成功模式的突变方向推荐
- 多目标权衡分析（TH vs IRI vs 表达量 vs 稳定性）
- 应用场景特定的优化建议
- 下一步具体操作建议""",
    current_sequence="string:当前AFP氨基酸序列",
    performance_data="string:当前性能数据JSON，如{\"th\":0.5,\"iri_ic50\":4.6,\"expression_score\":0.6,\"stability_score\":0.7}",
    design_target="string:设计目标描述，如'提高TH活性2倍'或'降低IRI IC50至1.0µM以下'",
    application_scenario="string:应用场景",
    design_history="string:已尝试的突变历史JSON数组（可选）"
)
def handle_design_strategy(current_sequence: str, performance_data: str = "{}",
                           design_target: str = "improve_activity",
                           application_scenario: str = "general",
                           design_history: str = "[]") -> dict:
    """生成设计策略"""
    seq = current_sequence.upper().strip()

    # 解析参数
    try:
        perf = json.loads(performance_data) if isinstance(performance_data, str) else performance_data
    except (json.JSONDecodeError, TypeError):
        perf = {}

    try:
        history = json.loads(design_history) if isinstance(design_history, str) else design_history
    except (json.JSONDecodeError, TypeError):
        history = []

    # 分析当前序列
    analysis = seq_analyzer.analyze(seq)

    # 获取场景权重
    scenario_weights = literature.get_scenario_weights(application_scenario)

    # 构建策略列表
    strategies = []

    # 策略1: TH优先
    if ("th" in design_target.lower() or "TH" in design_target or
        "热滞后" in design_target or "活性" in design_target):
        strategies.append({
            "priority": "HIGH",
            "strategy": "增强TH活性",
            "approach": [
                "增加IBS残基数量——更多Thr/Asn/Gln冰结合位点",
                "引入刚性化二硫键——降低结合熵损失",
                "优化Thr间距匹配冰晶格——靶向特定冰晶面",
                "考虑Glu(E)取代Thr——2025 JACS发现Glu结合能是Thr的4倍",
                "增加冰结合面面积——设计更长的重复序列"
            ],
            "forbidden": ["不可突变IBS核心残基", "不可在IBS引入大体积/带电残基"],
            "expected_improvement": "TH提升30-100%"
        })

    # 策略2: IRI优先
    if ("iri" in design_target.lower() or "IRI" in design_target or
        "重结晶" in design_target or "ice_cream" in application_scenario):
        strategies.append({
            "priority": "HIGH",
            "strategy": "增强IRI活性",
            "approach": [
                "增大冰结合面平坦面积——抑制冰重结晶需要大面积",
                "优化几何互补性——即使没有完美H-bond，几何匹配也能驱动IRI",
                "增加重复单元数量——更多IBS残基覆盖更大冰面",
                "考虑截短非活性区域——浓缩活性基序（如BtAFP策略）",
                "非IBS面空间敲除——测试非IBS残基对IRI的必要性"
            ],
            "forbidden": ["不可破坏IBS平坦性"],
            "expected_improvement": "IRI IC50降低30-60%"
        })

    # 策略3: 表达量优化
    if "表达" in design_target or "yield" in design_target.lower():
        strategies.append({
            "priority": "MEDIUM",
            "strategy": "提高表达产量",
            "approach": [
                "非IBS面Ala→Ser突变——提高溶解度",
                "添加MBP/GST融合标签——可提高表达量2-10倍",
                "优化Ala含量至40-55%——过高可能聚集",
                "避开连续疏水残基段——防止包涵体形成"
            ]
        })

    # 策略4: 稳定性优化
    if "稳定" in design_target or "stability" in design_target.lower():
        strategies.append({
            "priority": "MEDIUM",
            "strategy": "提高热稳定性",
            "approach": [
                "引入二硫键（偶数个Cys）——增强结构刚性",
                "增加Pro含量（适度）——刚性化骨架构象",
                "盐桥工程——Lys-Asp/Glu离子对稳定折叠",
                "芳香残基簇——pi-pi堆叠稳定核心"
            ]
        })

    if not strategies:
        strategies.append({
            "priority": "GENERAL",
            "strategy": "通用优化策略",
            "approach": [
                "非IBS面残基优化——提高溶解度和表达量",
                "IBS残基类型调优——Thr→Asn/Gln测试不同H-bond模式",
                "增加重复单元——扩大冰结合面积",
                "保守IBS核心——不触碰高度保守的功能残基"
            ]
        })

    # 推荐突变位点
    recommended_sites = []
    for hotspot in analysis.mutation_hotspots[:5]:
        recommended_sites.append({
            "position": hotspot["position"],
            "current": hotspot["current_aa"],
            "suggestion": hotspot["suggestion"],
            "potential": hotspot["mutation_potential"]
        })

    # 历史分析
    history_insights = "无历史数据——这是第一轮设计"
    if history:
        successes = len([h for h in history if h.get("verdict") == "PASS"])
        failures = len([h for h in history if h.get("verdict") == "REJECTED"])
        parts = []
        if successes > 0:
            parts.append(f"已有{successes}次成功突变")
        if failures > 0:
            parts.append(f"已有{failures}次失败——提示需避开禁区")
        history_insights = "; ".join(parts) if parts else "历史数据不足"

    return {
        "success": True,
        "current_state": {
            "afp_type": analysis.afp_type_prediction,
            "type_confidence": analysis.type_confidence,
            "estimated_th": analysis.estimated_th,
            "estimated_iri_ic50": analysis.estimated_iri_ic50,
            "design_potential": analysis.design_potential_score,
        },
        "scenario_weights": scenario_weights,
        "design_target": design_target,
        "strategies": strategies,
        "forbidden_positions": analysis.forbidden_positions[:10],
        "recommended_mutation_sites": recommended_sites,
        "key_principles": [
            {"title": p.title, "rule": p.rule}
            for p in literature.get_all_principles()[:5]
        ],
        "design_history_insights": history_insights,
        "next_step_suggestion": (
            f"建议优先实施{strategies[0]['strategy']}策略，"
            f"从推荐位点中选择1-3个进行突变，"
            f"避开禁区位置{analysis.forbidden_positions[:3]}"
        )
    }


# ============================================================
# 工具2: afp_design_summary —— 设计结果汇总
# ============================================================
@tool_registry.tool(
    name="afp_design_summary",
    description="""汇总抗冻蛋白设计全过程的结果，生成结构化的设计报告。包括:
- 原始序列和最终推荐序列对比
- 每一轮突变的路径和评估结果
- 性能变化趋势（TH/IRI/表达/稳定性）
- 成功的策略总结
- 应避免的突变类型
- 新发现的设计规则""",
    original_sequence="string:原始AFP序列",
    final_sequence="string:最终优化的AFP序列",
    design_target="string:设计目标描述",
    application_scenario="string:应用场景",
    mutation_history="string:各轮突变历史JSON数组，每轮包含mutations/verdict/th_change/iri_change/rationale",
    original_performance="string:原始性能JSON，如{\"th\":0.5,\"iri\":4.6,\"expression\":0.6,\"stability\":0.7}",
    final_performance="string:最终性能JSON，格式同上"
)
def handle_design_summary(original_sequence: str, final_sequence: str,
                           design_target: str = "",
                           application_scenario: str = "general",
                           mutation_history: str = "[]",
                           original_performance: str = "{}",
                           final_performance: str = "{}") -> dict:
    """汇总设计结果"""
    # 解析参数
    try:
        history = json.loads(mutation_history) if isinstance(mutation_history, str) else mutation_history
    except (json.JSONDecodeError, TypeError):
        history = []

    try:
        orig_perf = json.loads(original_performance) if isinstance(original_performance, str) else original_performance
    except (json.JSONDecodeError, TypeError):
        orig_perf = {}

    try:
        final_perf = json.loads(final_performance) if isinstance(final_performance, str) else final_performance
    except (json.JSONDecodeError, TypeError):
        final_perf = {}

    # 统计
    total_rounds = len(history)
    passed = sum(1 for r in history if r.get("verdict") == "PASS")
    rejected = sum(1 for r in history if r.get("verdict") == "REJECTED")
    warnings = sum(1 for r in history if r.get("verdict") == "WARNING")

    # 提取成功和失败的策略
    successful_strategies = []
    failed_strategies = []
    for r in history:
        v = r.get("verdict", "")
        if v == "PASS":
            successful_strategies.append(r.get("rationale", "")[:100])
        elif v == "REJECTED":
            failed_strategies.append(r.get("rationale", "")[:100])

    # 性能变化
    def _pct_change(old, new):
        if old == 0:
            return 100.0 if new > 0 else 0.0
        return round((new - old) / old * 100, 2)

    th_change = _pct_change(orig_perf.get("th", 0), final_perf.get("th", 0))
    iri_change = _pct_change(orig_perf.get("iri", 999), final_perf.get("iri", 999))
    expr_change = _pct_change(orig_perf.get("expression", 0), final_perf.get("expression", 0))

    return {
        "success": True,
        "design_overview": {
            "original_sequence": original_sequence,
            "final_sequence": final_sequence,
            "design_target": design_target,
            "application_scenario": application_scenario,
            "total_rounds": total_rounds,
            "passed": passed,
            "rejected": rejected,
            "warnings": warnings,
        },
        "mutation_path": [
            {
                "round": i + 1,
                "mutations": r.get("mutations", []),
                "verdict": r.get("verdict", "UNKNOWN"),
                "th_change": r.get("th_change", "N/A"),
                "iri_change": r.get("iri_change", "N/A"),
                "rationale": r.get("rationale", "")[:80],
            }
            for i, r in enumerate(history)
        ],
        "performance_comparison": {
            "th_c": {"original": orig_perf.get("th", "N/A"), "final": final_perf.get("th", "N/A"), "change_pct": th_change},
            "iri_ic50_uM": {"original": orig_perf.get("iri", "N/A"), "final": final_perf.get("iri", "N/A"), "change_pct": iri_change},
            "expression_score": {"original": orig_perf.get("expression", "N/A"), "final": final_perf.get("expression", "N/A"), "change_pct": expr_change},
            "stability_score": {"original": orig_perf.get("stability", "N/A"), "final": final_perf.get("stability", "N/A")},
        },
        "design_experience": {
            "successful_strategies": successful_strategies[:5],
            "failed_strategies": failed_strategies[:5],
            "key_lessons": [
                "非IBS面Ala→Ser亲水化: 安全性高，提高表达量",
                "IBS核心Thr→非极性残基: 活性崩溃(-80%)",
                "IBS面引入大体积残基: 破坏平面性",
                "IBS面引入带电残基(除Glu外): 排斥冰面",
                "Glu可部分替代Thr在IBS面增强冰结合(2025 JACS)"
            ],
        },
        "next_steps": [
            "将最终序列送交基因合成(C端6×His标签)",
            "毕赤酵母或大肠杆菌表达测试",
            "纳升渗透压计测TH活性",
            "蔗糖三明治法测IRI活性",
            "圆二色谱验证α-螺旋折叠",
        ]
    }


def register_all_tools():
    """注册所有策略工具"""
    pass
