# tools/afp_knowledge_tools.py
"""
AFP 知识库查询 + 序列分析工具
包含: afp_knowledge_query, afp_sequence_analyze
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge import AFPMotifLibrary, AFPLiteratureKnowledge, AFPSeqAnalyzer
from .registry import tool_registry

# 全局实例
motif_library = AFPMotifLibrary()
literature = AFPLiteratureKnowledge()
seq_analyzer = AFPSeqAnalyzer()


# ============================================================
# 工具1: afp_knowledge_query —— 知识库查询与多角度分析
# ============================================================
@tool_registry.tool(
    name="afp_knowledge_query",
    description="""查询抗冻蛋白知识库并对输入序列做多角度分析。返回:
- 序列匹配的已知AFP类型和置信度
- 冰结合面(IBS)残基识别和特征
- 已知基序的匹配结果
- 相关文献中的突变发现和设计原则
- 鉴定的禁区(不可突变的保守功能残基)
- 建议的可突变位点和方向""",
    sequence="string:AFP氨基酸序列（单字母代码，如DTASDAAAAAALTAANAKAAAELTAANAAAAAAATAR）",
    query_intent="string:查询意图，可选: full_analysis(完整分析,推荐)/ibs_only(仅冰结合面)/mutability(可突变性分析)/literature(文献查询)/classification(类型分类)",
    application_scenario="string:目标应用场景，可选: ice_cream/frozen_dough/meat_preservation/cell_cryopreservation/organ_preservation/transgenic_crop/anti_ice_coating/de_novo_optimization/general"
)
def handle_knowledge_query(sequence: str, query_intent: str = "full_analysis",
                           application_scenario: str = "general") -> dict:
    """查询知识库并分析序列"""
    seq = sequence.upper().strip()

    analysis = seq_analyzer.analyze(seq, query_intent)
    motif_matches = motif_library.search_by_sequence(seq)

    # 文献知识匹配
    relevant_principles_filtered = []
    for p in literature.get_all_principles()[:10]:
        for afp_type in p.applicable_afp_types:
            if afp_type.lower() in analysis.afp_type_prediction.lower():
                relevant_principles_filtered.append({
                    "title": p.title,
                    "rule": p.rule,
                    "evidence": p.evidence_strength,
                })
                break

    relevant_mutations = []
    for f in literature.findings:
        if analysis.afp_type_prediction != "Unknown":
            relevant_mutations.append({
                "protein": f.source_protein,
                "mutation": f.mutation,
                "th_change": f"{f.th_change_pct:+.1f}%",
                "iri_change": f"{f.iri_change_pct:+.1f}%",
                "mechanism": f.mechanism[:100],
            })

    scenario_weights = literature.get_scenario_weights(application_scenario)

    # 构建全序列位置→氨基酸对照（每10位换行，方便LLM快速定位）
    seq_map_lines = []
    for start in range(0, len(seq), 10):
        chunk = seq[start:start+10]
        positions = [f"{start+i+1}:{chunk[i]}" for i in range(len(chunk))]
        seq_map_lines.append("  " + " ".join(positions))
    position_guide = "\n".join(seq_map_lines)

    return {
        "success": True,
        "sequence": seq,
        "length": len(seq),
        "query_intent": query_intent,
        "application_scenario": application_scenario,
        "scenario_weights": scenario_weights,
        "position_guide": position_guide,
        "afp_type_prediction": analysis.afp_type_prediction,
        "type_confidence": analysis.type_confidence,
        "type_scores": analysis.type_scores,
        "top_motif_matches": motif_matches[:5],
        "predicted_ibs": {
            "positions": analysis.predicted_ibs_positions[:20],
            "residues": analysis.predicted_ibs_residues[:20],
            "target_ice_plane": analysis.predicted_ice_plane,
        },
        "physicochemical_summary": {
            "thr_content": round(analysis.thr_content, 3),
            "ala_content": round(analysis.ala_content, 3),
            "cys_content": round(analysis.cys_content, 3),
            "net_charge": analysis.net_charge,
            "gravy": round(analysis.gravy, 3),
            "isoelectric_point": analysis.isoelectric_point,
            "instability_index": round(analysis.instability_index, 2),
        },
        "forbidden_positions": analysis.forbidden_positions[:20],
        "mutation_hotspots": analysis.mutation_hotspots[:10],
        "design_potential_score": round(analysis.design_potential_score, 3),
        "activity_prediction": {
            "estimated_th_C": analysis.estimated_th,
            "estimated_iri_IC50_uM": analysis.estimated_iri_ic50,
            "expression_score": round(analysis.estimated_expression_score, 3),
            "stability_score": round(analysis.estimated_stability_score, 3),
        },
        "relevant_design_principles": relevant_principles_filtered[:8],
        "relevant_mutations": relevant_mutations[:8],
    }


# ============================================================
# 工具2: afp_sequence_analyze —— 专注序列分析
# ============================================================
@tool_registry.tool(
    name="afp_sequence_analyze",
    description="""对AFP序列进行三级分析管道（基序扫描→类型分类→全长评估）。返回:
- AFP类型预测和置信度评分
- 冰结合面(IBS)残基精确定位
- 物理化学特征（Thr/Ala/Cys含量、净电荷、GRAVY、pI、不稳定指数）
- 突变热点和设计潜力评分
- 活性预测（TH/IRI/表达/稳定性）""",
    sequence="string:AFP氨基酸序列",
    application_scenario="string:应用场景，默认general"
)
def handle_sequence_analyze(sequence: str, application_scenario: str = "general") -> dict:
    """对输入序列进行三级分析"""
    seq = sequence.upper().strip()
    analysis = seq_analyzer.analyze(seq)

    return {
        "success": True,
        "sequence": seq,
        "length": len(seq),
        "afp_type_prediction": analysis.afp_type_prediction,
        "type_confidence": round(analysis.type_confidence, 4),
        "type_scores": {k: round(v, 3) for k, v in analysis.type_scores.items()},
        "predicted_ibs": {
            "positions": analysis.predicted_ibs_positions[:20],
            "residues": analysis.predicted_ibs_residues[:20],
            "target_ice_plane": analysis.predicted_ice_plane,
        },
        "physicochemical": {
            "thr_content": round(analysis.thr_content, 3),
            "ala_content": round(analysis.ala_content, 3),
            "cys_content": round(analysis.cys_content, 3),
            "net_charge_ph7": analysis.net_charge,
            "gravy": round(analysis.gravy, 3),
            "isoelectric_point": analysis.isoelectric_point,
            "instability_index": round(analysis.instability_index, 2),
        },
        "forbidden_positions": analysis.forbidden_positions[:20],
        "mutation_hotspots": analysis.mutation_hotspots[:10],
        "design_potential_score": round(analysis.design_potential_score, 3),
        "activity_prediction": {
            "estimated_th_C": analysis.estimated_th,
            "estimated_iri_IC50_uM": analysis.estimated_iri_ic50,
            "expression_score": round(analysis.estimated_expression_score, 3),
            "stability_score": round(analysis.estimated_stability_score, 3),
        },
    }


def register_all_tools():
    """注册所有知识库工具"""
    pass
