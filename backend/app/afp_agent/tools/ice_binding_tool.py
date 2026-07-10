"""
AFP冰结合模拟工具 — 模拟抗冻蛋白与冰晶面的几何匹配与结合亲和力
注册为: afp_ice_bind_simulate
"""

from app.afp_agent.tools.registry import registry
from app.afp_agent.simulator.ice_binding import (
    AFPIceBindingSimulator,
    IcePlane,
    IceBindingResult,
    ComparisonResult,
)


def ice_binding_handler(args: dict) -> dict:
    """
    模拟抗冻蛋白冰结合能力。

    参数:
        sequence: 抗冻蛋白氨基酸序列
        original_sequence: 原始序列（用于对比）
        ibs_positions: 已知/推测的冰结合面残基位置列表（1-indexed）
        target_ice_plane: "auto" | "basal" | "prism" | "pyramidal_201" | "pyramidal_110"
    """
    sequence = args.get("sequence", "").upper()
    original_sequence = args.get("original_sequence", "").upper() or None
    ibs_positions = args.get("ibs_positions", None)
    target_ice_plane = args.get("target_ice_plane", "auto")

    if not sequence:
        return {"error": "请提供氨基酸序列"}

    # 解析冰晶面
    plane = _resolve_ice_plane(sequence, target_ice_plane)

    # 创建模拟器实例
    simulator = AFPIceBindingSimulator()

    # 运行冰结合模拟
    result: IceBindingResult = simulator.simulate(
        sequence=sequence,
        ibs_positions=ibs_positions,
        target_plane=plane,
    )

    output = result.to_dict()
    output["target_ice_plane"] = plane.value if hasattr(plane, "value") else str(plane)

    # 如果提供了原始序列，生成对比
    if original_sequence and original_sequence != sequence:
        comparison: ComparisonResult = simulator.compare(
            original_seq=original_sequence,
            mutated_seq=sequence,
            ibs_positions=ibs_positions,
        )

        output["comparison"] = {
            "th_change_pct": comparison.th_change_pct,
            "iri_change_pct": comparison.iri_change_pct,
            "geometry_change": comparison.geometry_change,
            "assessment": comparison.assessment,
            "recommendation": comparison.recommendation,
            "original_result": comparison.original.to_dict(),
        }

    return output


def _resolve_ice_plane(sequence: str, target: str) -> IcePlane:
    """
    自动检测最佳匹配冰晶面或解析用户指定平面。

    Auto检测策略: 基于残基间距与冰晶面氧原子间距的匹配度。
    """
    if target != "auto":
        plane_map = {
            "basal": IcePlane.BASAL,
            "prism": IcePlane.PRISM,
            "pyramidal_201": IcePlane.PYRAMIDAL_201,
            "pyramidal_110": IcePlane.PYRAMIDAL_110,
        }
        return plane_map.get(target, IcePlane.PRISM)

    # Auto-detect: 分析序列中 T/N/Q 残基间距模式
    ibs_like = [i for i, aa in enumerate(sequence, 1) if aa in ('T', 'N', 'Q')]

    if len(ibs_like) < 2:
        return IcePlane.PRISM  # 默认棱面

    # 计算平均间距
    spacings = []
    for i in range(len(ibs_like)):
        for j in range(i + 1, len(ibs_like)):
            spacings.append(abs(ibs_like[j] - ibs_like[i]) * 3.5)  # ~3.5Å per residue

    avg_spacing = sum(spacings) / len(spacings)

    # 匹配最近的冰晶面氧间距
    best_plane = IcePlane.PRISM
    best_diff = float("inf")
    for plane, info in {
        IcePlane.BASAL: 7.35,
        IcePlane.PRISM: 4.52,
        IcePlane.PYRAMIDAL_201: 16.5,
        IcePlane.PYRAMIDAL_110: 7.85,
    }.items():
        # 检查 spacing 是否接近 lattice 常数的整数倍
        for n in range(1, 5):
            diff = abs(avg_spacing - n * info) / (n * info)
            if diff < best_diff:
                best_diff = diff
                best_plane = plane

    return best_plane


# 注册工具
registry.register(
    name="afp_ice_bind_simulate",
    toolset="afp",
    schema={
        "type": "function",
        "function": {
            "name": "afp_ice_bind_simulate",
            "description": (
                "模拟抗冻蛋白与冰晶面的几何匹配与结合亲和力。"
                "三层评分: 几何互补性 + 物理化学特征 + 经验活性模型。"
                "输出: geometry_score, spacing_match_score, residue_quality_score, "
                "flatness_prediction, estimated_iri_activity, estimated_th_activity。"
                "支持与原始序列的对比评估。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {
                        "type": "string",
                        "description": "抗冻蛋白氨基酸序列（单字母）",
                    },
                    "original_sequence": {
                        "type": "string",
                        "description": "原始序列（可选，提供时自动生成对比评估）",
                    },
                    "ibs_positions": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "已知/推测的冰结合面残基位置（1-indexed），留空则自动检测",
                    },
                    "target_ice_plane": {
                        "type": "string",
                        "enum": ["auto", "basal", "prism", "pyramidal_201", "pyramidal_110"],
                        "description": "靶向冰晶面: auto(自动检测), basal(基面{0001}), prism(棱面{10-10}), pyramidal_201(锥面{20-21}), pyramidal_110(锥面{11-20})",
                    },
                },
                "required": ["sequence"],
            },
        },
    },
    handler=lambda args, **kw: ice_binding_handler(args),
    description="模拟AFP冰结合：几何匹配、活性估计、突变对比",
    emoji="❄️",
)
