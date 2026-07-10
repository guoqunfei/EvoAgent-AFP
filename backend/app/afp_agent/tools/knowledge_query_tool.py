"""
AFP知识查询工具 — 查询抗冻蛋白知识库中的冰结合基序、突变效应和设计原则
注册为: afp_knowledge_query
"""

from app.afp_agent.knowledge.knowledge_base import AFPKnowledgeBase
from app.afp_agent.tools.registry import registry

# 模块级变量：在 agent 初始化时注入知识库实例
_kb: AFPKnowledgeBase = None


def set_knowledge_base(kb: AFPKnowledgeBase):
    """注入知识库实例（由 Agent 初始化时调用）"""
    global _kb
    _kb = kb


def knowledge_query_handler(args: dict) -> dict:
    """
    查询抗冻蛋白知识库。

    参数:
        sequence: 氨基酸序列（单字母）
        query_intent: full_analysis | ibs_only | mutability | literature | classification
        application_scenario: ice_cream | frozen_dough | meat_preservation |
                             cell_cryopreservation | organ_preservation |
                             transgenic_crop | anti_ice_coating | general
    """
    sequence = args.get("sequence", "").upper()
    query_intent = args.get("query_intent", "full_analysis")
    application_scenario = args.get("application_scenario", "general")

    if not sequence:
        return {"error": "请提供氨基酸序列"}

    valid_intents = {"full_analysis", "ibs_only", "mutability", "literature", "classification"}
    if query_intent not in valid_intents:
        return {"error": f"无效的查询意图: {query_intent}，可选值: {valid_intents}"}

    valid_scenarios = {
        "ice_cream", "frozen_dough", "meat_preservation",
        "cell_cryopreservation", "organ_preservation",
        "transgenic_crop", "anti_ice_coating", "general"
    }
    scenario = application_scenario if application_scenario in valid_scenarios else "general"

    if _kb is None:
        # 回退：尝试实例化知识库
        try:
            kb = AFPKnowledgeBase()
        except Exception:
            return {"error": "知识库未初始化，请稍后重试"}
    else:
        kb = _kb

    try:
        analysis = kb.analyze_sequence(sequence, application_scenario=scenario)
    except AttributeError:
        return {"error": "知识库不支持 analyze_sequence 方法"}
    except Exception as e:
        return {"error": f"知识库查询失败: {str(e)}"}

    # analysis is an AFPKnowledgeQuery dataclass — use attribute access
    from dataclasses import asdict

    if query_intent == "ibs_only":
        result = {
            "sequence": sequence,
            "length": len(sequence),
            "ibs_residues": analysis.ibs_residues_identified,
            "matched_motifs": analysis.matched_motifs,
        }
    elif query_intent == "mutability":
        result = {
            "sequence": sequence,
            "length": len(sequence),
            "forbidden_regions": analysis.forbidden_regions,
            "mutation_candidates": analysis.mutation_candidates,
        }
    elif query_intent == "literature":
        result = {
            "sequence": sequence,
            "length": len(sequence),
            "literature_findings": analysis.literature_findings_matched,
            "design_principles": analysis.design_principles_matched,
        }
    elif query_intent == "classification":
        result = {
            "sequence": sequence,
            "length": len(sequence),
            "afp_type": analysis.afp_type_prediction,
            "confidence": analysis.confidence,
        }
    else:  # full_analysis
        result = asdict(analysis)
        result["sequence"] = sequence
        result["length"] = len(sequence)
        result["scenario"] = scenario

    result["query_intent"] = query_intent
    result["application_scenario"] = scenario
    return result


# 注册工具
registry.register(
    name="afp_knowledge_query",
    toolset="afp",
    schema={
        "type": "function",
        "function": {
            "name": "afp_knowledge_query",
            "description": (
                "查询抗冻蛋白知识库，获取冰结合基序模式、突变效应预测和蛋白设计原则。"
                "支持多种查询意图: 全量分析(full_analysis)、冰结合面分析(ibs_only)、"
                "突变可行性(mutability)、文献资料(literature)、AFP分类(classification)。"
                "覆盖应用场景: 冰淇淋、冷冻面团、肉类保鲜、细胞冻存、器官保存、转基因作物、防冰涂层。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {
                        "type": "string",
                        "description": "抗冻蛋白的氨基酸序列（单字母）",
                    },
                    "query_intent": {
                        "type": "string",
                        "enum": [
                            "full_analysis",
                            "ibs_only",
                            "mutability",
                            "literature",
                            "classification",
                        ],
                        "description": "查询意图: full_analysis(全面分析), ibs_only(冰结合面), mutability(突变可行性), literature(文献), classification(分类)",
                    },
                    "application_scenario": {
                        "type": "string",
                        "enum": [
                            "ice_cream",
                            "frozen_dough",
                            "meat_preservation",
                            "cell_cryopreservation",
                            "organ_preservation",
                            "transgenic_crop",
                            "anti_ice_coating",
                            "general",
                        ],
                        "description": "应用场景: ice_cream(冰淇淋), frozen_dough(冷冻面团), meat_preservation(肉类保鲜), cell_cryopreservation(细胞冻存), organ_preservation(器官保存), transgenic_crop(转基因作物), anti_ice_coating(防冰涂层), general(通用)",
                    },
                },
                "required": ["sequence"],
            },
        },
    },
    handler=lambda args, **kw: knowledge_query_handler(args),
    description="查询AFP知识库：冰结合基序、突变效应、设计原则",
    emoji="📚",
)
