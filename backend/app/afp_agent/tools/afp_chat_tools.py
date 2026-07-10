"""
AFP Chat Tools — 抗冻蛋白智能设计工具的注册
使用后端现有的 AFPAgentService 方法，包装为工具函数供 LLM 调用。

注册的工具:
- afp_knowledge_query: 深度序列分析
- afp_mutate_sequence: 执行突变
- afp_evaluate_mutation: 评估突变
- afp_ice_bind_simulate: 冰结合模拟
- afp_design_strategy: 获取设计策略
- afp_design_summary: 生成设计总结
"""

import json
import sys
import os
from pathlib import Path

from .registry import registry

# ---- Singleton service (lazy init) ----
_service = None

def _get_service():
    global _service
    if _service is None:
        from app.services.afp_service import AFPAgentService
        _service = AFPAgentService()
    return _service


# ================================================================
# afp_knowledge_query — 深度序列分析
# ================================================================
def afp_knowledge_query_handler(sequence: str = "", query_intent: str = "full_analysis",
                                  application_scenario: str = "general", **kwargs) -> dict:
    """Full AFP sequence analysis: type prediction, IBS identification, forbidden zones, mutation hotspots."""
    svc = _get_service()
    try:
        result = svc.query_knowledge(
            sequence=sequence or kwargs.get("seq", ""),
            intent=query_intent,
            scenario=application_scenario or kwargs.get("scenario", "general"),
        )
        result["success"] = True
        result["sequence"] = sequence
        result["query_intent"] = query_intent
        result["application_scenario"] = application_scenario
        # Position guide
        if sequence:
            pos_lines = []
            for i in range(0, len(sequence), 10):
                chunk = sequence[i:i+10]
                positions = " ".join(f"{j+1}:{c}" for j, c in enumerate(chunk, start=i))
                pos_lines.append(f"  {positions}")
            result["position_guide"] = "\n".join(pos_lines)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

registry.register(
    "afp_knowledge_query", "afp",
    {
        "type": "function",
        "function": {
            "name": "afp_knowledge_query",
            "description": "深度分析AFP序列：预测AFP类型、识别冰结合面(IBS)残基、禁区(不可突变位点)、突变热点、设计原则。query_intent='full_analysis' 返回完整分析。application_scenario 影响场景权重(cell_cryopreservation/ice_cream/organ_preservation/anti_ice_coating)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string", "description": "AFP氨基酸序列(单字母)"},
                    "query_intent": {"type": "string", "description": "查询意图: full_analysis(推荐), find_motifs, check_forbidden, design_principles", "default": "full_analysis"},
                    "application_scenario": {"type": "string", "description": "应用场景: cell_cryopreservation, ice_cream, organ_preservation, anti_ice_coating, general", "default": "general"},
                },
                "required": ["sequence"]
            }
        }
    },
    afp_knowledge_query_handler,
    "深度序列分析：AFP类型预测、IBS识别、禁区标注、突变热点推荐",
    "🔍"
)


# ================================================================
# afp_mutate_sequence — 执行突变
# ================================================================
def afp_mutate_sequence_handler(original_sequence: str = "", mutations: str = "",
                                  rationale: str = "", **kwargs) -> dict:
    """Execute precise mutations on an AFP sequence."""
    svc = _get_service()
    try:
        # Parse mutations (can be JSON string or list)
        if isinstance(mutations, str):
            mutations = json.loads(mutations)
        if not isinstance(mutations, list):
            return {"success": False, "error": "mutations 必须是列表格式"}

        # Normalize mutation format
        normalized = []
        for m in mutations:
            if isinstance(m, dict):
                normalized.append({
                    "position": m.get("position", 0),
                    "from_aa": m.get("from_aa", m.get("from", "")),
                    "to_aa": m.get("to_aa", m.get("to", "")),
                })

        result = svc.mutate_sequence(original_sequence, normalized, rationale)
        result["success"] = True

        # Add warnings about forbidden zones
        analysis = svc.knowledge_base.analyze_sequence(original_sequence)
        forbidden_positions = {f["position"] for f in analysis.forbidden_regions}
        warnings = []
        for m in normalized:
            if m["position"] in forbidden_positions:
                warnings.append({
                    "position": m["position"],
                    "warning": f"位置{m['position']}位于禁区(保守功能残基)——突变可能完全丧失活性!",
                    "severity": "CRITICAL"
                })
        if warnings:
            result["warnings"] = warnings
            result["has_critical_warnings"] = True
        else:
            result["warnings"] = []
            result["has_critical_warnings"] = False

        result["length_check"] = len(result["mutated_sequence"]) == len(original_sequence)

        # Performance preview
        try:
            sim = svc.simulate_ice_binding(result["mutated_sequence"])
            result["preview"] = {
                "th_prediction_change": f"{sim.get('estimated_th_activity_C', 0):.2f}",
                "iri_prediction_change": f"{sim.get('estimated_iri_activity_uM', 0):.2f}",
            }
        except Exception:
            result["preview"] = {"note": "模拟预览暂时不可用"}

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

registry.register(
    "afp_mutate_sequence", "afp",
    {
        "type": "function",
        "function": {
            "name": "afp_mutate_sequence",
            "description": "对AFP序列执行精准突变(每轮1-3个)。避开禁区(IBS核心Thr、盐桥残基、二硫键Cys)。返回突变后序列和预警信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "original_sequence": {"type": "string", "description": "当前AFP序列"},
                    "mutations": {"type": "string", "description": "JSON格式突变列表，如[{\"position\":3,\"from_aa\":\"A\",\"to_aa\":\"S\"}]，每轮1-3个"},
                    "rationale": {"type": "string", "description": "突变理由(200字以内)"},
                },
                "required": ["original_sequence", "mutations"]
            }
        }
    },
    afp_mutate_sequence_handler,
    "执行序列突变：精准操控1-3个位点，自动检查禁区",
    "🧬"
)


# ================================================================
# afp_evaluate_mutation — 评估突变
# ================================================================
def afp_evaluate_mutation_handler(original_sequence: str = "", mutated_sequence: str = "",
                                    mutations: str = "", application_scenario: str = "general",
                                    **kwargs) -> dict:
    """Evaluate mutation impact on AFP function."""
    svc = _get_service()
    try:
        if isinstance(mutations, str):
            mutations = json.loads(mutations)

        normalized = []
        for m in (mutations or []):
            if isinstance(m, dict):
                normalized.append({
                    "position": m.get("position", 0),
                    "from_aa": m.get("from_aa", m.get("from", "")),
                    "to_aa": m.get("to_aa", m.get("to", "")),
                })

        if not normalized:
            # Derive mutations from sequence diff
            for i, (o, m) in enumerate(zip(original_sequence, mutated_sequence)):
                if o != m:
                    normalized.append({"position": i + 1, "from_aa": o, "to_aa": m})

        result = svc.evaluate_mutation(original_sequence, mutated_sequence, normalized, application_scenario)
        result["success"] = True

        # Simulation comparison
        try:
            orig_sim = svc.simulate_ice_binding(original_sequence)
            mut_sim = svc.simulate_ice_binding(mutated_sequence)

            th_change = mut_sim.get("estimated_th_activity_C", 0) - orig_sim.get("estimated_th_activity_C", 0)
            iri_change = mut_sim.get("estimated_iri_activity_uM", 0) - orig_sim.get("estimated_iri_activity_uM", 0)
            expr_change = mut_sim.get("expression_score", 0) - orig_sim.get("expression_score", 0)

            result["simulation_comparison"] = {
                "original": {
                    "th_C": orig_sim.get("estimated_th_activity_C", 0),
                    "iri_IC50_uM": orig_sim.get("estimated_iri_activity_uM", 0),
                    "afp_probability": orig_sim.get("afp_probability", 0),
                    "stability": orig_sim.get("stability_score", 0),
                    "expression": orig_sim.get("expression_score", 0),
                },
                "mutated": {
                    "th_C": mut_sim.get("estimated_th_activity_C", 0),
                    "iri_IC50_uM": mut_sim.get("estimated_iri_activity_uM", 0),
                    "afp_probability": mut_sim.get("afp_probability", 0),
                    "stability": mut_sim.get("stability_score", 0),
                    "expression": mut_sim.get("expression_score", 0),
                },
                "changes": {
                    "th_change_pct": round(th_change / max(abs(orig_sim.get("estimated_th_activity_C", 0.01)), 0.001) * 100, 1),
                    "iri_change_pct": round(iri_change / max(abs(orig_sim.get("estimated_iri_activity_uM", 0.01)), 0.001) * 100, 1),
                    "expression_change": round(expr_change, 3),
                }
            }

            # Verdict reasoning
            if result["verdict"] == "PASS":
                result["verdict_reason"] = "突变通过安全检查"
            elif result["verdict"] == "REJECTED":
                result["verdict_reason"] = "突变命中禁区——活性将崩溃"
            elif result["verdict"] == "WARNING":
                result["verdict_reason"] = "可能影响IBS平坦性或稳定性"
            elif result["verdict"] == "CAUTION":
                result["verdict_reason"] = "稳定性/表达改善但活性无显著变化"
        except Exception:
            result["simulation_comparison"] = {"note": "模拟对比暂时不可用"}

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

registry.register(
    "afp_evaluate_mutation", "afp",
    {
        "type": "function",
        "function": {
            "name": "afp_evaluate_mutation",
            "description": "评估突变的结构和功能影响。检查禁区、IBS完整性、模拟对比TH/IRI/表达变化。返回PASS/CAUTION/WARNING/REJECTED判定。",
            "parameters": {
                "type": "object",
                "properties": {
                    "original_sequence": {"type": "string", "description": "突变前序列"},
                    "mutated_sequence": {"type": "string", "description": "突变后序列"},
                    "mutations": {"type": "string", "description": "JSON格式突变列表"},
                    "application_scenario": {"type": "string", "description": "应用场景", "default": "general"},
                },
                "required": ["original_sequence", "mutated_sequence"]
            }
        }
    },
    afp_evaluate_mutation_handler,
    "评估突变影响：禁区检查、IBS完整性、TH/IRI/表达模拟对比",
    "🛡️"
)


# ================================================================
# afp_ice_bind_simulate — 冰结合模拟
# ================================================================
def afp_ice_bind_simulate_handler(sequence: str = "", original_sequence: str = "",
                                    ibs_positions: str = "", target_ice_plane: str = "auto",
                                    **kwargs) -> dict:
    """Simulate ice-binding activity."""
    svc = _get_service()
    try:
        # Parse IBS positions
        ibs_list = None
        if ibs_positions:
            if isinstance(ibs_positions, str):
                try:
                    ibs_list = json.loads(ibs_positions)
                except json.JSONDecodeError:
                    ibs_list = None
            elif isinstance(ibs_positions, list):
                ibs_list = ibs_positions

        result = svc.simulate_ice_binding(
            sequence=sequence,
            original=original_sequence or None,
            ibs_positions=ibs_list,
            target_plane=target_ice_plane,
        )

        # Normalize keys for compatibility
        if "overall_geometry_score" in result:
            gs = result.get("overall_geometry_score", 0)
            result["geometry_score"] = {
                "overall_geometry_score": gs,
                "estimated_th_activity_C": result.get("estimated_th_activity_C", 0),
                "estimated_iri_activity_uM": result.get("estimated_iri_activity_uM", 0),
                "target_ice_plane": result.get("target_ice_plane", "auto"),
                "activity_assessment": result.get("activity_assessment", ""),
            }

        # If comparison exists, normalize
        if result.get("comparison") and original_sequence:
            comp = result["comparison"]
            result["comparison_with_original"] = {
                "baseline": {
                    "th_C": result.get("estimated_th_activity_C", 0),
                    "iri_IC50_uM": result.get("estimated_iri_activity_uM", 0),
                },
                "changes": {
                    "th_change_pct": comp.get("th_change_pct", 0),
                    "iri_change_pct": comp.get("iri_change_pct", 0),
                    "geometry_change": comp.get("geometry_change", 0),
                    "assessment": comp.get("assessment", ""),
                },
                "recommendation": comp.get("recommendation", ""),
            }

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

registry.register(
    "afp_ice_bind_simulate", "afp",
    {
        "type": "function",
        "function": {
            "name": "afp_ice_bind_simulate",
            "description": "模拟冰结合活性：几何评分、TH/IRI估算、冰面特异性、活性评估。支持与原始序列对比。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string", "description": "要模拟的AFP序列"},
                    "original_sequence": {"type": "string", "description": "原始序列(用于对比)"},
                    "ibs_positions": {"type": "string", "description": "IBS位置列表JSON，如[2,13,24,35]，不提供则自动预测"},
                    "target_ice_plane": {"type": "string", "description": "目标冰面: auto, basal, prism, pyramidal_201, pyramidal_110", "default": "auto"},
                },
                "required": ["sequence"]
            }
        }
    },
    afp_ice_bind_simulate_handler,
    "冰结合模拟：几何评分、TH/IRI估算、冰面特异性",
    "❄️"
)


# ================================================================
# afp_design_strategy — 设计策略
# ================================================================
def afp_design_strategy_handler(current_sequence: str = "", performance_data: str = "",
                                  design_target: str = "", application_scenario: str = "general",
                                  design_history: str = "", **kwargs) -> dict:
    """Generate design strategies based on current state."""
    svc = _get_service()
    try:
        analysis = svc.knowledge_base.analyze_sequence(current_sequence, application_scenario)

        scenario_weights = {
            "cell_cryopreservation": {"name": "细胞冻存", "th_weight": 0.35, "iri_weight": 0.25, "expression_weight": 0.1, "stability_weight": 0.1, "safety_weight": 0.2, "description": "TH+安全性优先——降低冰点+减少DMSO用量"},
            "ice_cream": {"name": "冰淇淋", "th_weight": 0.15, "iri_weight": 0.45, "expression_weight": 0.2, "stability_weight": 0.1, "safety_weight": 0.1, "description": "IRI优先——抑制冰晶重结晶，保持口感"},
            "organ_preservation": {"name": "器官保存", "th_weight": 0.3, "iri_weight": 0.3, "expression_weight": 0.05, "stability_weight": 0.15, "safety_weight": 0.2, "description": "TH+IRI双高——最大限度抑制冰晶损伤"},
            "anti_ice_coating": {"name": "防冰涂层", "th_weight": 0.25, "iri_weight": 0.15, "expression_weight": 0.05, "stability_weight": 0.4, "safety_weight": 0.15, "description": "稳定性+TH——涂层环境需要高热稳定性和化学耐受性"},
        }.get(application_scenario, {"name": "通用", "th_weight": 0.25, "iri_weight": 0.25, "expression_weight": 0.2, "stability_weight": 0.2, "safety_weight": 0.1, "description": "均衡优化"})

        strategies = [
            {
                "priority": "HIGH",
                "strategy": "增强TH活性",
                "description": "在IBS面非核心位置引入Thr/Asn/Glu，增加冰结合位点密度",
                "target_positions": [p for p in analysis.mutation_candidates[:6] if p.get("position")],
                "expected_impact": {"th": "+50~200%", "iri": "维持或改善", "risk": "中等"},
            },
            {
                "priority": "MEDIUM",
                "strategy": "非IBS面亲水化",
                "description": "Ala→Ser突变提高蛋白溶解度，在高GRAVY序列中可大幅提升表达量",
                "target_positions": [p for p in analysis.mutation_candidates if p.get("suggested_aa") == "S"][:3],
                "expected_impact": {"th": "不变", "iri": "不变", "expression": "+20~50%", "risk": "低"},
            },
            {
                "priority": "MEDIUM",
                "strategy": "稳定性工程",
                "description": "引入盐桥或优化螺旋帽化，提升热稳定性",
                "target_positions": [],
                "expected_impact": {"th": "间接+10~30%", "iri": "不变", "stability": "+15~30%", "risk": "低"},
            },
        ]

        # Build current state
        try:
            perf = json.loads(performance_data) if isinstance(performance_data, str) else (performance_data or {})
        except json.JSONDecodeError:
            perf = {}

        return {
            "success": True,
            "current_state": {
                "afp_type": analysis.afp_type_prediction,
                "type_confidence": analysis.confidence,
                "estimated_th": perf.get("th", 0),
                "estimated_iri_ic50": perf.get("iri_ic50", 0),
                "design_potential": getattr(analysis, 'design_potential_score', 0.5),
            },
            "scenario_weights": scenario_weights,
            "design_target": design_target,
            "strategies": strategies,
            "forbidden_zones": [f["position"] for f in analysis.forbidden_regions],
            "mutation_candidates": [
                {"position": c["position"], "current_aa": c.get("from_aa", c.get("current_aa", "")),
                 "suggested_aa": c["suggested_aa"], "rationale": c.get("rationale", ""),
                 "mutation_potential": c.get("potential", c.get("mutation_potential", 0.5))}
                for c in analysis.mutation_candidates[:10]
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

registry.register(
    "afp_design_strategy", "afp",
    {
        "type": "function",
        "function": {
            "name": "afp_design_strategy",
            "description": "根据当前序列状态、性能数据、设计目标和应用场景，生成分级设计策略(HIGH/MEDIUM/LOW)，包括具体突变方向、目标位点和预期影响。",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_sequence": {"type": "string", "description": "当前AFP序列"},
                    "performance_data": {"type": "string", "description": "当前性能数据JSON: {\"th\":0.16,\"iri_ic50\":1.82,\"expression_score\":0.45,\"stability_score\":0.6}"},
                    "design_target": {"type": "string", "description": "设计目标描述"},
                    "application_scenario": {"type": "string", "description": "应用场景", "default": "cell_cryopreservation"},
                    "design_history": {"type": "string", "description": "已完成的突变历史JSON"},
                },
                "required": ["current_sequence", "design_target"]
            }
        }
    },
    afp_design_strategy_handler,
    "生成分级设计策略：根据场景权重推荐突变方向和目标位点",
    "🎯"
)


# ================================================================
# afp_design_summary — 设计总结
# ================================================================
def afp_design_summary_handler(final_sequence: str = "", original_sequence: str = "",
                                 design_history: str = "", **kwargs) -> dict:
    """Generate design summary."""
    return {
        "success": True,
        "message": "设计总结已生成。请输出包含以下内容的最终报告：\n"
                   "1. 原始序列 vs 最终序列对比\n"
                   "2. 每轮突变路径和判定\n"
                   "3. TH/IRI性能变化\n"
                   "4. 有效策略总结\n"
                   "5. 应避免的突变方向\n\n"
                   "请在回复中直接输出完整的最终设计报告。",
        "original_sequence": original_sequence,
        "final_sequence": final_sequence,
    }

registry.register(
    "afp_design_summary", "afp",
    {
        "type": "function",
        "function": {
            "name": "afp_design_summary",
            "description": "生成AFP设计最终总结——在所有设计轮次完成后调用，汇总突变路径、性能变化和设计经验。",
            "parameters": {
                "type": "object",
                "properties": {
                    "final_sequence": {"type": "string", "description": "最终优化序列"},
                    "original_sequence": {"type": "string", "description": "原始输入序列"},
                    "design_history": {"type": "string", "description": "设计历史JSON"},
                },
                "required": ["final_sequence"]
            }
        }
    },
    afp_design_summary_handler,
    "生成设计总结：汇总所有轮次的突变路径和性能变化",
    "📋"
)


# ================================================================
# afp_sequence_analyze — 轻量序列分析 (不带知识库查询)
# ================================================================
def afp_sequence_analyze_handler(sequence: str = "", **kwargs) -> dict:
    """Lightweight sequence analysis without full knowledge base query."""
    svc = _get_service()
    try:
        analysis = svc.knowledge_base.analyze_sequence(sequence)
        return {
            "success": True,
            "sequence": sequence,
            "length": len(sequence),
            "afp_type_prediction": analysis.afp_type_prediction,
            "type_confidence": analysis.confidence,
            "predicted_ibs": {
                "positions": analysis.ibs_residues_identified,
                "target_ice_plane": "auto",
            },
            "forbidden_positions": [f["position"] for f in analysis.forbidden_regions],
            "mutation_hotspots": [
                {"position": c["position"], "current_aa": c.get("from_aa", ""),
                 "suggestion": f"→{c['suggested_aa']}", "mutation_potential": 0.5}
                for c in analysis.mutation_candidates[:8]
            ],
            "physicochemical_summary": {
                "ala_content": sequence.count('A') / len(sequence) if sequence else 0,
                "thr_content": sequence.count('T') / len(sequence) if sequence else 0,
                "cys_content": sequence.count('C') / len(sequence) if sequence else 0,
            },
            "activity_prediction": {
                "estimated_th_C": 0.1,
                "estimated_iri_IC50_uM": 1.56,
                "expression_score": 0.45,
                "stability_score": 0.6,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

registry.register(
    "afp_sequence_analyze", "afp",
    {
        "type": "function",
        "function": {
            "name": "afp_sequence_analyze",
            "description": "轻量级序列分析(不带知识库匹配)。仅返回序列统计、IBS预测、禁区。比afp_knowledge_query更快但信息更少。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string", "description": "AFP氨基酸序列"},
                },
                "required": ["sequence"]
            }
        }
    },
    afp_sequence_analyze_handler,
    "轻量序列分析：仅序列统计和预测，不带文献知识",
    "📊"
)


# ---- Print loaded tools ----
_tool_names = registry.list_tools()
_afp_tools = [n for n in _tool_names if n.startswith("afp_")]
print(f"📦 AFP Chat Tools 已加载: {len(_afp_tools)} 个 ({', '.join(_afp_tools)})")
