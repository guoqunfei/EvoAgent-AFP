# tools/afp_simulation_tools.py
"""
AFP 冰结合模拟（虚拟实验）工具
包含: afp_ice_bind_simulate
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge import AFPSeqAnalyzer
from simulator import AFPSimulator
from simulator.geometry_scorer import IceBindingGeometryScorer, IcePlane
from .registry import tool_registry

seq_analyzer = AFPSeqAnalyzer()
simulator = AFPSimulator()


@tool_registry.tool(
    name="afp_ice_bind_simulate",
    description="""执行抗冻蛋白冰结合简化模拟（虚拟实验）。基于几何评分+物理化学特征+经验模型:
- 计算IBS-冰面几何互补性评分（对所有4种冰面）
- 估算冰结合自由能
- 预测TH和IRI活性值
- 对比突变前后的活性变化
- 找到最佳匹配冰面
- 给出活性评估（超活性/中等/低/无活性）""",
    sequence="string:AFP氨基酸序列",
    original_sequence="string:原始AFP序列（用于对比，可选，不提供则不对比）",
    ibs_positions="string:IBS残基位置JSON数组，如[2,13,24,35]（可选，不提供则自动推断）",
    target_ice_plane="string:靶向冰晶面，可选: basal/prism/pyramidal_201/pyramidal_110/auto(自动推断)，默认auto"
)
def handle_ice_bind_simulate(sequence: str, original_sequence: str = "",
                              ibs_positions: str = "[]",
                              target_ice_plane: str = "auto") -> dict:
    """执行冰结合模拟"""
    seq = sequence.upper().strip()

    # 解析IBS位置
    try:
        if isinstance(ibs_positions, str):
            ibs_list = json.loads(ibs_positions)
        else:
            ibs_list = ibs_positions
    except (json.JSONDecodeError, TypeError):
        ibs_list = []

    if not ibs_list:
        analysis = seq_analyzer.analyze(seq, "ibs_only")
        ibs_list = analysis.predicted_ibs_positions

    # 确定靶向冰面
    plane_map = {
        "basal": IcePlane.BASAL,
        "prism": IcePlane.PRISM,
        "pyramidal_201": IcePlane.PYRAMIDAL_201,
        "pyramidal_110": IcePlane.PYRAMIDAL_110,
    }

    if target_ice_plane == "auto" or target_ice_plane not in plane_map:
        geo_scorer = IceBindingGeometryScorer()
        best_plane, best_score = geo_scorer.find_best_plane(seq, ibs_list)
        plane = best_plane
    else:
        plane = plane_map[target_ice_plane]

    # 运行模拟
    sim_result = simulator.simulate(seq, ibs_list, plane)

    # 如果有原始序列，做对比
    comparison = None
    if original_sequence:
        orig_seq = original_sequence.upper().strip()
        comparison = simulator.compare(orig_seq, seq)

    result = sim_result.to_dict()
    result["success"] = True
    result["ibs_positions_used"] = ibs_list

    if comparison:
        result["comparison_with_original"] = comparison

    return result


def register_all_tools():
    """注册所有模拟工具"""
    pass
