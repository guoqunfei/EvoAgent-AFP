# tools/afp_visualize_tools.py
"""
AFP 可视化工具
包含: afp_visualize_trajectory
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .registry import tool_registry


@tool_registry.tool(
    name="afp_visualize_trajectory",
    description="""生成抗冻蛋白设计的性能变化轨迹图。返回图表文件路径。
图表包含4个子图: TH活性变化、IRI活性变化、表达/稳定性评分变化、AFP概率变化。
在design_record/{session_id}/trajectory.png生成PNG图表。""",
    round_data="string:各轮设计数据的JSON数组，格式[{'round':1,'th_value':0.1,'iri_value':1.5,'expression_score':0.6,'stability_score':0.6,'afp_probability':0.9},...]",
    baseline="string:基线性能JSON，如{'th':0.16,'iri':1.82,'expression':0.452,'stability':0.606}（可选）"
)
def handle_visualize_trajectory(round_data: str, baseline: str = "{}") -> dict:
    """生成性能变化轨迹图"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return {"success": False, "error": "matplotlib 未安装，请运行 pip install matplotlib"}

    try:
        if isinstance(round_data, str):
            rounds = json.loads(round_data)
        else:
            rounds = round_data
    except (json.JSONDecodeError, TypeError):
        return {"success": False, "error": "round_data 格式错误"}

    try:
        if isinstance(baseline, str):
            base = json.loads(baseline)
        else:
            base = baseline
    except (json.JSONDecodeError, TypeError):
        base = {}

    if not rounds:
        return {"success": False, "error": "轮次数据为空"}

    # 设置字体
    plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    rnums = [r.get("round", i+1) for i, r in enumerate(rounds)]
    th_vals = [r.get("th_value", 0) for r in rounds]
    iri_vals = [r.get("iri_value", 0) for r in rounds]
    expr_vals = [r.get("expression_score", 0) for r in rounds]
    stab_vals = [r.get("stability_score", 0) for r in rounds]
    afp_probs = [r.get("afp_probability", 0) for r in rounds]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("AFP Design Performance Trajectory", fontsize=14, fontweight="bold")

    # TH
    ax1 = axes[0][0]
    ax1.plot(rnums, th_vals, "o-", color="#E74C3C", lw=2, ms=6)
    ax1.set_xlabel("Round"); ax1.set_ylabel("TH (C)")
    ax1.set_title("TH Activity"); ax1.grid(True, alpha=0.3)
    if base.get("th"):
        ax1.axhline(y=base["th"], color="gray", ls="--", alpha=0.5)

    # IRI
    ax2 = axes[0][1]
    ax2.plot(rnums, iri_vals, "o-", color="#3498DB", lw=2, ms=6)
    ax2.set_xlabel("Round"); ax2.set_ylabel("IRI IC50 (uM)")
    ax2.set_title("IRI Activity"); ax2.grid(True, alpha=0.3)
    if base.get("iri"):
        ax2.axhline(y=base["iri"], color="gray", ls="--", alpha=0.5)

    # Expression + Stability
    ax3 = axes[1][0]
    ax3.plot(rnums, expr_vals, "o-", color="#2ECC71", lw=2, ms=6, label="Expression")
    ax3.plot(rnums, stab_vals, "s--", color="#F39C12", lw=2, ms=6, label="Stability")
    ax3.set_xlabel("Round"); ax3.set_ylabel("Score"); ax3.legend()
    ax3.set_title("Expression & Stability"); ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0, 1.1)

    # AFP Probability
    ax4 = axes[1][1]
    ax4.plot(rnums, afp_probs, "o-", color="#9B59B6", lw=2, ms=6)
    ax4.set_xlabel("Round"); ax4.set_ylabel("AFP Probability")
    ax4.set_title("AFP Probability"); ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0, 1.05)
    ax4.axhline(y=0.9, color="green", ls="--", alpha=0.5)

    plt.tight_layout()

    # 保存到当前会话的 images/ 目录（自动发现最新会话）
    base_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "design_record"
    )
    os.makedirs(base_dir, exist_ok=True)

    # 查找最新会话目录
    session_dirs = sorted([
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
        and not d.startswith(".")
    ], reverse=True)

    if session_dirs:
        # 使用已有会话目录
        target_session = session_dirs[0]
        images_dir = os.path.join(base_dir, target_session, "images")
    else:
        # 无会话时创建独立的可视化目录
        from datetime import datetime as dt
        images_dir = os.path.join(base_dir, "visualizations")
    os.makedirs(images_dir, exist_ok=True)

    chart_path = os.path.join(images_dir, "trajectory.png")
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()

    return {
        "success": True,
        "chart_path": chart_path,
        "rounds_plotted": len(rounds),
        "final_th": th_vals[-1] if th_vals else 0,
        "final_iri": iri_vals[-1] if iri_vals else 0,
    }


def register_all_tools():
    """注册可视化工具"""
    pass
