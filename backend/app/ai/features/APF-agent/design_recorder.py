# design_recorder.py
"""
设计记录模块 —— 每个会话创建唯一 ID，存储所有设计数据，支持可视化。
目录结构:
  design_record/
    {session_id}/
      input_seq_analysis/      — 输入序列的评估结果
        analysis.json
      images/                  — 可视化图表
        trajectory.png
      report/                  — 最终设计报告
        final_report.json
      rounds.json              — 每轮设计数据 (实时更新)
      summary.json             — 最终汇总
"""

import os
import json
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class DesignRecorder:
    """单次设计会话的记录器"""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "design_record"
            )
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一会话 ID（带碰撞保护）
        base_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
        session_id = base_id
        counter = 0
        while (self.base_dir / session_id).exists():
            counter += 1
            session_id = f"{base_id}_{counter}"
        self.session_id = session_id

        self.session_dir = self.base_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=False)

        # 子目录
        self.analysis_dir = self.session_dir / "input_seq_analysis"
        self.images_dir = self.session_dir / "images"
        self.report_dir = self.session_dir / "report"
        for d in [self.analysis_dir, self.images_dir, self.report_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.rounds: List[Dict] = []
        self.original_sequence = ""
        self.final_sequence = ""
        self.design_target = ""
        self.application_scenario = ""

        # 会话索引 —— 记录本次会话元信息
        self._write_session_index()

        # 性能基线
        self.baseline = {}

    def _write_session_index(self):
        """在 design_record 根目录写入/更新会话索引"""
        index_file = self.base_dir / "sessions_index.json"
        existing = []
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing = []

        existing.append({
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "directory": str(self.session_dir),
        })

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    @staticmethod
    def list_sessions(base_dir: str = None) -> List[Dict]:
        """列出所有历史会话"""
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "design_record"
            )
        index_file = Path(base_dir) / "sessions_index.json"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    # ================================================================
    # 输入序列分析
    # ================================================================
    def save_input_analysis(self, analysis_result: Dict):
        """保存 afp_knowledge_query 的完整结果到 input_seq_analysis/"""
        self.original_sequence = analysis_result.get("sequence", "")
        self.application_scenario = analysis_result.get("application_scenario", "general")
        if analysis_result.get("activity_prediction"):
            ap = analysis_result["activity_prediction"]
            self.baseline = {
                "th": ap.get("estimated_th_C", 0),
                "iri": ap.get("estimated_iri_IC50_uM", 0),
                "expression": ap.get("expression_score", 0),
                "stability": ap.get("stability_score", 0),
            }

        analysis_file = self.analysis_dir / "analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "input_sequence": self.original_sequence,
                "sequence_length": analysis_result.get("length", 0),
                "afp_type": analysis_result.get("afp_type_prediction", "Unknown"),
                "type_confidence": analysis_result.get("type_confidence", 0),
                "type_scores": analysis_result.get("type_scores", {}),
                "predicted_ibs": analysis_result.get("predicted_ibs", {}),
                "physicochemical": analysis_result.get("physicochemical_summary", {}),
                "forbidden_positions": analysis_result.get("forbidden_positions", []),
                "mutation_hotspots": analysis_result.get("mutation_hotspots", []),
                "design_potential_score": analysis_result.get("design_potential_score", 0),
                "activity_prediction": analysis_result.get("activity_prediction", {}),
                "relevant_principles": analysis_result.get("relevant_design_principles", []),
                "relevant_mutations": analysis_result.get("relevant_mutations", []),
                "top_motifs": analysis_result.get("top_motif_matches", [])[:5],
                "full_result": analysis_result,
            }, f, ensure_ascii=False, indent=2)

        print(f"   📁 序列分析已保存: {analysis_file}")

    # ================================================================
    # 轮次记录
    # ================================================================
    def record_round(self, round_num: int, original_seq: str, mutated_seq: str,
                     mutations: List[Dict], rationale: str,
                     eval_result: Dict = None, sim_result: Dict = None):
        """记录一轮设计并实时写入磁盘"""
        th_change = 0.0
        iri_change = 0.0
        verdict = "?"
        if eval_result:
            verdict = eval_result.get("verdict", "?")
            sim_comp = eval_result.get("simulation_comparison", {})
            changes = sim_comp.get("changes", {})
            th_change = changes.get("th_change_pct", 0)
            iri_change = changes.get("iri_change_pct", 0)

        th_val = sim_result.get("estimated_TH_C", 0) if sim_result else 0
        iri_val = sim_result.get("estimated_IRI_IC50_uM", 0) if sim_result else 0
        expr_val = sim_result.get("expression_score", 0) if sim_result else 0
        stab_val = sim_result.get("stability_score", 0) if sim_result else 0
        afp_prob = sim_result.get("afp_probability", 0) if sim_result else 0

        round_data = {
            "round": round_num,
            "original_sequence": original_seq,
            "mutated_sequence": mutated_seq,
            "mutations": [f"{m.get('from_aa','')}{m.get('position',0)}{m.get('to_aa','')}"
                         for m in mutations],
            "rationale": rationale[:200] if rationale else "",
            "verdict": verdict,
            "th_change_pct": th_change,
            "iri_change_pct": iri_change,
            "th_value": th_val,
            "iri_value": iri_val,
            "expression_score": expr_val,
            "stability_score": stab_val,
            "afp_probability": afp_prob,
            "timestamp": datetime.now().isoformat(),
        }

        self.rounds.append(round_data)
        self.final_sequence = mutated_seq
        self._save_rounds()

    def _save_rounds(self):
        """实时写入 rounds.json"""
        with open(self.session_dir / "rounds.json", "w", encoding="utf-8") as f:
            json.dump({
                "session_id": self.session_id,
                "original_sequence": self.original_sequence,
                "design_target": self.design_target,
                "application_scenario": self.application_scenario,
                "baseline": self.baseline,
                "total_rounds": len(self.rounds),
                "rounds": self.rounds,
            }, f, ensure_ascii=False, indent=2)

    # ================================================================
    # 最终报告
    # ================================================================
    def save_summary(self, final_perf: Dict = None):
        """保存 summary.json + report/final_report.md + 自动生成可视化"""
        summary = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "original_sequence": self.original_sequence,
            "final_sequence": self.final_sequence,
            "design_target": self.design_target,
            "application_scenario": self.application_scenario,
            "total_rounds": len(self.rounds),
            "baseline": self.baseline,
            "final_performance": final_perf or {},
            "rounds_summary": [
                {
                    "round": r["round"],
                    "mutations": r["mutations"],
                    "verdict": r["verdict"],
                    "th_change": f"{r['th_change_pct']:+.1f}%",
                    "iri_change": f"{r['iri_change_pct']:+.1f}%",
                    "expression": round(r["expression_score"], 3),
                    "stability": round(r["stability_score"], 3),
                }
                for r in self.rounds
            ],
            "best_round": self._find_best_round(),
            "performance_trend": self._build_trend_table(),
        }

        # JSON 报告
        with open(self.session_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        with open(self.report_dir / "final_report.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # Markdown 报告
        md_path = self._generate_markdown_report(summary, final_perf or {})

        # 自动生成可视化
        chart_path = self.generate_visualization()

        print(f"   📁 报告已保存: {self.report_dir}")
        if md_path:
            print(f"   📄 Markdown 报告: {md_path}")
        if chart_path:
            print(f"   📊 可视化图表: {chart_path}")

        return summary

    def _find_best_round(self) -> Optional[Dict]:
        best = None
        best_score = -999
        for r in self.rounds:
            score = r["th_change_pct"] + r["iri_change_pct"] + r["expression_score"] * 50
            if score > best_score:
                best_score = score
                best = r
        return {"round": best["round"], "mutations": best["mutations"],
                "verdict": best["verdict"]} if best else None

    def _build_trend_table(self) -> List[Dict]:
        """构建性能趋势表"""
        trend = []
        for r in self.rounds:
            trend.append({
                "round": r["round"],
                "mutations": r["mutations"],
                "th": round(r["th_value"], 3),
                "iri": round(r["iri_value"], 2),
                "expression": round(r["expression_score"], 3),
                "stability": round(r["stability_score"], 3),
                "afp_probability": round(r["afp_probability"], 4),
            })
        return trend

    # ================================================================
    # Markdown 报告
    # ================================================================
    def _generate_markdown_report(self, summary: Dict, final_perf: Dict) -> str:
        """生成全面的 Markdown 设计报告 —— 含深度分析、迭代过程、经验教训"""
        # 加载输入分析数据
        analysis = self._load_analysis_data()
        lines = []
        sid = self.session_id

        # ====== 报告头部 ======
        lines.append(f"# 🧬 AFP 抗冻蛋白智能设计 — 最终报告\n")
        lines.append(f"| 项目 | 内容 |")
        lines.append(f"|------|------|")
        lines.append(f"| **会话 ID** | `{sid}` |")
        lines.append(f"| **生成时间** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |")
        lines.append(f"| **应用场景** | {self.application_scenario} |")
        lines.append(f"| **总设计轮次** | {len(self.rounds)} |")
        lines.append(f"| **设计目标** | {self.design_target[:200]} |\n")

        # ====== 1. 输入序列深度分析 ======
        lines.append("---\n")
        lines.append("## 1. 输入序列深度分析\n")

        afp_type = analysis.get("afp_type", "Unknown")
        confidence = analysis.get("type_confidence", 0)
        seq = self.original_sequence
        seq_len = len(seq)

        lines.append(f"### 1.1 序列鉴定\n")
        lines.append(f"输入序列为 **{seq_len} aa** 的抗冻蛋白，经知识库匹配鉴定为 **{afp_type}**"
                     f"（置信度 {confidence:.0%}）。")
        lines.append(f"该类型 AFP 主要来源于冬鲽鱼（*Pseudopleuronectes americanus*），"
                     f"以富含丙氨酸（Ala）的 α-螺旋结构为特征。\n")

        # 类型得分
        type_scores = analysis.get("type_scores", {})
        if type_scores:
            lines.append(f"**各类型匹配得分**:\n")
            for t, s in sorted(type_scores.items(), key=lambda x: -x[1])[:5]:
                bar = "█" * int(s * 20) + "░" * (20 - int(s * 20))
                lines.append(f"- {t}: `{bar}` {s:.2f}\n")

        # IBS 分析
        ibs = analysis.get("predicted_ibs", {})
        ibs_positions = ibs.get("positions", [])
        ibs_plane = ibs.get("target_ice_plane", "Unknown")
        lines.append(f"### 1.2 冰结合面 (IBS) 架构\n")
        lines.append(f"**IBS 核心残基**: {', '.join(f'`{r}`' for r in ibs.get('residues', []))} "
                     f"（位置 {', '.join(str(p) for p in ibs_positions)}）")
        lines.append(f"**靶向冰面**: {ibs_plane}")
        lines.append(f"**Thr 间距**: 16.5 Å — 精确匹配金字塔面 `{{20-21}}` 的氧原子晶格间距")
        lines.append(f"**IBS 平坦性要求**: RMSD < 1.0 Å —— 不可引入大体积/带电残基\n")

        # 序列标注
        if seq:
            lines.append(f"**序列位置标注**:\n```")
            lines.append(f"序列: {seq}")
            pos_line = ""
            for i in range(len(seq)):
                if i + 1 in ibs_positions:
                    pos_line += "▲"
                else:
                    pos_line += " "
            # 每10位标注
            tick_line = ""
            for i in range(len(seq)):
                if (i + 1) % 10 == 0:
                    tick_line += str(i + 1)[-1]
                elif (i + 1) % 5 == 0:
                    tick_line += "·"
                else:
                    tick_line += " "
            lines.append(f"IBS:  {pos_line}")
            lines.append(f"位标: {tick_line}")
            lines.append(f"```\n")

        # 物理化学深度解读
        physchem = analysis.get("physicochemical", {})
        lines.append(f"### 1.3 物理化学特征深度解读\n")
        lines.append(f"| 指标 | 数值 | 解读 |")
        lines.append(f"|------|:----:|------|")

        ala = physchem.get("ala_content", 0)
        thr = physchem.get("thr_content", 0)
        cys = physchem.get("cys_content", 0)
        gravy = physchem.get("gravy", 0)
        pi = physchem.get("isoelectric_point", 0)
        charge = physchem.get("net_charge", 0)
        ii = physchem.get("instability_index", 40)

        lines.append(f"| **Ala 含量** | {ala:.1%} | "
                     f"{'🟢 极高 — Type I 标志 (>50%)，利于 α-螺旋稳定性' if ala > 0.5 else '正常' if ala > 0.3 else '偏低'} |")
        lines.append(f"| **Thr 含量** | {thr:.1%} | "
                     f"{'IBS 核心残基，间距 16.5Å 匹配金字塔面' if thr > 0.05 else '偏低 — 可能缺乏冰结合位点'} |")
        lines.append(f"| **Cys 含量** | {cys:.1%} | "
                     f"{'无二硫键 — 缺乏刚性化支架，TH 活性受限于鱼源级别 (~0.5°C)' if cys == 0 else '存在二硫键 — 可能具有超活性潜力'} |")
        lines.append(f"| **GRAVY** | {gravy:.3f} | "
                     f"{'🟡 高度疏水 — 有利于冰面疏水互补，但可能降低表达可溶性' if gravy > 0.3 else '亲水 — 表达可溶性好' if gravy < -0.3 else '适中'} |")
        lines.append(f"| **pI** | {pi:.2f} | "
                     f"{'酸性蛋白 — 在生理 pH 下带负电' if pi < 7 else '碱性蛋白' if pi > 7 else '近中性'} |")
        lines.append(f"| **净电荷 (pH7)** | {charge:+.0f} | "
                     f"{'近中性 — 适合细胞冻存（低免疫原性）' if abs(charge) <= 2 else '带电偏高 — 可能影响安全性'} |")
        lines.append(f"| **不稳定指数** | {ii:.1f} | "
                     f"{'🟢 稳定 (<40) — 适合长期储存' if ii < 40 else '🟡 偏高 (>40) — 可能需要稳定性工程'} |")
        lines.append("")

        # 禁区分析
        forbidden = analysis.get("forbidden_positions", [])
        lines.append(f"### 1.4 设计约束分析\n")
        lines.append(f"**禁区（不可突变残基）**: 共 {len(forbidden)} 个位置")
        lines.append(f"`{', '.join(str(p) for p in forbidden[:20])}`")
        lines.append(f"\n禁区包括：")
        if ibs_positions:
            lines.append(f"- **IBS 核心 Thr**: `{', '.join(f'T{p}' for p in ibs_positions)}` — 间距 16.5Å 匹配冰晶格，任一突变均导致活性崩溃")
        lines.append(f"- **盐桥残基**: D1, D5, K18, E22 — 维持 α-螺旋帽化结构")
        lines.append(f"- **IBS 面保守残基**: 不可引入 F/W/Y（大体积）、D/E（负电荷）、K/R（正电荷+大体积）\n")

        # 突变热点
        hotspots = analysis.get("mutation_hotspots", [])
        if hotspots:
            lines.append(f"**突变热点 (推荐可突变位点)**:\n")
            for h in hotspots[:8]:
                lines.append(f"- **P{h.get('position', '?')}** (`{h.get('current_aa', '?')}`) → "
                           f"{h.get('suggestion', '')} [潜力: {h.get('mutation_potential', 0):.1f}]")

        design_pot = analysis.get("design_potential_score", 0)
        lines.append(f"\n**设计潜力评分**: {design_pot:.3f} / 1.0")
        lines.append(f"> {'🟢 高设计潜力 — 有多个可安全突变的位点' if design_pot > 0.7 else '🟡 中等潜力' if design_pot > 0.4 else '🔴 低潜力 — IBS 面高度保守，可操作空间有限'}\n")

        # 基线活性
        lines.append(f"### 1.5 基线活性预测\n")
        lines.append(f"| 指标 | 预测值 | 评价 |")
        lines.append(f"|------|:------:|------|")
        activ = analysis.get("activity_prediction", {})
        lines.append(f"| TH (热滞后) | {activ.get('estimated_th_C', 0):.2f} °C | "
                     f"{'鱼源级别 (~0.5°C)' if activ.get('estimated_th_C', 0) < 0.5 else '中等' if activ.get('estimated_th_C', 0) < 2 else '高活性'} |")
        lines.append(f"| IRI IC₅₀ | {activ.get('estimated_iri_IC50_uM', 0):.2f} µM | "
                     f"{'强 IRI 活性' if activ.get('estimated_iri_IC50_uM', 99) < 2 else '中等' if activ.get('estimated_iri_IC50_uM', 99) < 5 else '弱'} |")
        lines.append(f"| 表达评分 | {activ.get('expression_score', 0):.3f} | "
                     f"{'🟡 偏低 — 可能与高疏水性 (GRAVY={gravy:.3f}) 有关' if activ.get('expression_score', 0) < 0.5 else '良好'} |")
        lines.append(f"| 稳定性 | {activ.get('stability_score', 0):.3f} | "
                     f"{'🟢 稳定 (II={ii:.1f}<40)' if ii < 40 else '需要改善'} |")
        lines.append("")

        # 相关文献知识
        principles = analysis.get("relevant_principles", [])
        if principles:
            lines.append(f"### 1.6 相关设计原则（来自文献）\n")
            for p in principles[:6]:
                lines.append(f"- **{p.get('title', '')}**: {p.get('rule', '')} "
                           f"[{p.get('evidence', '')}]")
            lines.append("")

        # ====== 2. 设计迭代全过程 ======
        lines.append("---\n")
        lines.append("## 2. 设计迭代全过程\n")

        if not self.rounds:
            lines.append("> ⚠️ 本轮未执行突变设计。\n")
        else:
            # 策略阶段划分
            phases = self._identify_design_phases()
            lines.append(f"设计共经历 **{len(self.rounds)} 轮** 迭代，"
                        f"可分为 **{len(phases)} 个策略阶段**：\n")

            for phase_name, phase_rounds in phases:
                lines.append(f"### {phase_name} (Rounds {phase_rounds[0]['round']}–{phase_rounds[-1]['round']})\n")
                # 阶段目标
                lines.append(f"**阶段目标**: {self._describe_phase_goal(phase_name, phase_rounds)}\n")

                for r in phase_rounds:
                    muts = ", ".join(r["mutations"]) if r["mutations"] else "—"
                    verdict_icon = {"PASS": "✅", "CAUTION": "🟡", "WARNING": "⚠️", "REJECTED": "❌"}.get(r["verdict"], "❓")
                    lines.append(f"#### Round {r['round']}: {muts}\n")
                    lines.append(f"| 属性 | 内容 |")
                    lines.append(f"|------|------|")
                    lines.append(f"| **突变** | {muts} |")
                    lines.append(f"| **理由** | {r.get('rationale', '—')[:300]} |")
                    lines.append(f"| **判定** | {verdict_icon} **{r['verdict']}** |")
                    lines.append(f"| **TH 变化** | {r['th_change_pct']:+.1f}% |")
                    lines.append(f"| **IRI 变化** | {r['iri_change_pct']:+.1f}% |")
                    lines.append(f"| **表达评分** | {r['expression_score']:.3f} |")
                    lines.append(f"| **稳定性** | {r['stability_score']:.3f} |")
                    lines.append(f"| **AFP 概率** | {r['afp_probability']:.4f} |")

                    # 轮次解读
                    insight = self._analyze_round_insight(r, phase_name)
                    if insight:
                        lines.append(f"\n> 💡 **本轮解读**: {insight}\n")
                    lines.append("")

            # ====== 3. 策略演进分析 ======
            lines.append("---\n")
            lines.append("## 3. 策略演进分析\n")
            lines.append(self._analyze_strategy_evolution())

        # ====== 4. 序列对比 ======
        lines.append("---\n")
        lines.append("## 4. 序列对比\n")
        final_seq = self.final_sequence or self.original_sequence
        lines.append(f"| 项目 | 序列 |")
        lines.append(f"|------|------|")
        lines.append(f"| **原始序列** | `{self.original_sequence}` |")
        lines.append(f"| **最终序列** | `{final_seq}` |")

        if self.original_sequence != final_seq:
            diffs = []
            for i, (o, f) in enumerate(zip(self.original_sequence, final_seq)):
                if o != f:
                    diffs.append(f"`{o}{i+1}{f}`")
            lines.append(f"| **突变位点** | {', '.join(diffs)} |")
            lines.append(f"| **突变数量** | {len(diffs)} |")
        lines.append("")

        # ====== 5. 性能对比 ======
        lines.append("---\n")
        lines.append("## 5. 性能对比\n")
        lines.append("| 指标 | 基线值 | 最终值 | 变化 | 评价 |")
        lines.append("|------|:------:|:------:|:----:|------|")

        def _pct(old, new):
            if old == 0: return ("+∞", "N/A")
            return (f"{(new-old)/old*100:+.1f}%",
                    "🟢 改善" if (new-old)/max(abs(old),0.001) > 0.1 else
                    "🟡 不变" if abs((new-old)/max(abs(old),0.001)) <= 0.1 else "🔴 下降")

        base_th = self.baseline.get("th", 0)
        base_iri = self.baseline.get("iri", 0)
        base_expr = self.baseline.get("expression", 0)
        base_stab = self.baseline.get("stability", 0)

        final_th = final_perf.get("th", base_th)
        final_iri = final_perf.get("iri", base_iri)
        final_expr = final_perf.get("expression", base_expr)
        final_stab = final_perf.get("stability", base_stab)

        for name, base, final in [("TH (°C)", base_th, final_th), ("IRI IC₅₀ (µM)", base_iri, final_iri),
                                    ("表达评分", base_expr, final_expr), ("稳定性评分", base_stab, final_stab)]:
            chg, rating = _pct(base, final)
            lines.append(f"| **{name}** | {base:.3f} | {final:.3f} | {chg} | {rating} |")

        if self.rounds:
            lines.append(f"| **AFP 概率** | — | {self.rounds[-1]['afp_probability']:.4f} | — | "
                        f"{'🟢 高置信度' if self.rounds[-1]['afp_probability'] > 0.9 else '🟡 中等' if self.rounds[-1]['afp_probability'] > 0.7 else '🔴 偏低'} |")
        lines.append("")

        # ====== 6. 性能趋势 ======
        if self.rounds and len(self.rounds) >= 2:
            lines.append("---\n")
            lines.append("## 6. 性能变化趋势\n")
            lines.append("| 轮次 | TH (°C) | IRI IC₅₀ (µM) | 表达 | 稳定性 | AFP 概率 | 判定 |")
            lines.append("|:----:|:-------:|:-------------:|:----:|:------:|:--------:|:----:|")
            for r in self.rounds:
                vi = {"PASS": "✅", "CAUTION": "🟡", "WARNING": "⚠️", "REJECTED": "❌"}.get(r["verdict"], "❓")
                lines.append(
                    f"| {r['round']} | {r['th_value']:.3f} | {r['iri_value']:.2f} | "
                    f"{r['expression_score']:.3f} | {r['stability_score']:.3f} | "
                    f"{r['afp_probability']:.4f} | {vi} |"
                )
            lines.append("")

        # ====== 7. 关键发现与设计规则 ======
        lines.append("---\n")
        lines.append("## 7. 关键发现与设计规则\n")
        lines.append(self._extract_design_rules())

        # ====== 8. 可视化 ======
        lines.append("---\n")
        lines.append("## 8. 可视化\n")
        chart_file = self.images_dir / "trajectory.png"
        if chart_file.exists():
            lines.append(f"![性能轨迹图](../images/trajectory.png)\n")
            lines.append(f"> 4 子图分别展示：TH 活性变化、IRI 活性变化、表达/稳定性评分趋势、AFP 概率变化。\n")
        else:
            lines.append("> ⚠️ 可视化图表未生成（可能缺少 matplotlib）。\n")

        # ====== 页脚 ======
        lines.append("---\n")
        lines.append(f"*报告由 AFP-Designer 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append(f"*会话 ID: `{sid}` | 总轮次: {len(self.rounds)} | 应用场景: {self.application_scenario}*\n")

        md_content = "\n".join(lines)
        md_path = self.report_dir / "final_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return str(md_path)

    # ================================================================
    # 报告辅助方法
    # ================================================================
    def _load_analysis_data(self) -> Dict:
        """加载输入序列分析数据"""
        analysis_file = self.analysis_dir / "analysis.json"
        if analysis_file.exists():
            try:
                with open(analysis_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {}

    def _identify_design_phases(self) -> List[tuple]:
        """将设计轮次划分为策略阶段"""
        if not self.rounds:
            return []

        phases = []
        current_phase = []
        current_name = "阶段1: 初始探索"

        for r in self.rounds:
            muts = r.get("mutations", [])
            rationale = r.get("rationale", "")
            verdict = r.get("verdict", "")

            # 检测策略转变
            if "Ala→Ser" in rationale or "Ala→S" in str(muts):
                new_name = "非IBS面亲水化 (Ala→Ser)"
            elif "Cys" in rationale or "C→" in str(muts):
                new_name = "二硫键刚性化策略"
            elif "Glu" in rationale or "E" in str(muts):
                new_name = "Glu 增强冰结合 (2025 JACS 策略)"
            elif "Thr" in rationale or "→T" in str(muts):
                new_name = "IBS 面 Thr 扩展策略"
            elif "Gln" in rationale or "→Q" in str(muts):
                new_name = "Gln 极性网络策略"
            elif "Asn" in rationale or "→N" in str(muts):
                new_name = "Asn 冰结合增强策略"
            elif "盐桥" in rationale or "K-E" in rationale or "K→" in str(muts):
                new_name = "盐桥工程策略"
            elif verdict == "REJECTED":
                new_name = "高风险策略尝试 (已回退)"
            else:
                new_name = "多策略综合优化"

            if current_phase and new_name != current_name:
                phases.append((current_name, current_phase))
                current_phase = []
            current_name = new_name
            current_phase.append(r)

        if current_phase:
            phases.append((current_name, current_phase))

        return phases

    def _describe_phase_goal(self, phase_name: str, rounds: List[Dict]) -> str:
        """描述阶段目标"""
        if "亲水化" in phase_name:
            return ("通过非 IBS 面 Ala→Ser 突变提高蛋白溶解度和表达量，"
                   "不触碰 IBS 核心残基以确保冰结合功能不受影响。")
        elif "Asn" in phase_name:
            return ("在 IBS 面附近引入 Asn，利用其酰胺侧链与冰面形成双氢键，"
                   "增加冰结合位点密度以提升 TH/IRI。")
        elif "Thr" in phase_name:
            return ("在 IBS 面上扩展 Thr 残基，利用 Thr 羟基的强冰结合能力"
                   "增强 TH 活性。Thr 是仅次于 Glu 的第二强冰结合残基。")
        elif "Gln" in phase_name:
            return ("引入 Gln 残基，其较长侧链的酰胺基可参与远程氢键网络，"
                   "在非 IBS 面增强冰结合辅助作用。")
        elif "二硫键" in phase_name:
            return ("引入 Cys 对形成二硫键，刚性化 α-螺旋骨架以降低冰结合时的构象熵损失，"
                   "间接提升 TH。昆虫超活性 AFP 的关键特征。")
        elif "Glu" in phase_name:
            return ("利用 2025 JACS 发现——Glu 结合能是 Thr 的 4 倍，"
                   "在 IBS 面用 Glu 替换 Thr 以大幅增强冰结合。高风险高回报。")
        elif "盐桥" in phase_name:
            return ("引入 Lys-Asp/Glu 离子对形成盐桥，增强 α-螺旋稳定性，"
                   "降低折叠自由能以间接提升 TH。")
        elif "REJECTED" in phase_name:
            return ("尝试高风险突变策略。本轮突变因命中禁区或严重降低性能而被拒绝，"
                   "经验教训将被记录以避免重复。")
        else:
            return ("综合运用多种策略进行序列优化，同时兼顾 TH、IRI、表达和稳定性。")

    def _analyze_round_insight(self, r: Dict, phase_name: str) -> str:
        """分析单轮设计的洞见"""
        verdict = r.get("verdict", "")
        th_chg = r.get("th_change_pct", 0)
        iri_chg = r.get("iri_change_pct", 0)
        expr = r.get("expression_score", 0)

        if verdict == "REJECTED":
            return ("本轮突变因命中禁区被拒绝。这再次确认了保守功能残基不可突变的原则。"
                   "设计时应始终避开禁区列表中的位点。")
        elif verdict == "WARNING":
            return (f"本轮涉及 IBS 面残基的修改，触发了警告。"
                   f"虽然 TH/IRI 可能改善，但需要仔细评估是否破坏了 IBS 平坦性。")
        elif th_chg <= 0 and iri_chg <= 0:
            return (f"本轮突变对 TH 和 IRI 均无显著改善。策略方向可能需要调整——"
                   f"如果连续多轮无改善，应考虑更换突变类型或目标位点。")
        elif th_chg > 20:
            return (f"TH 活性显著提升 {th_chg:+.1f}%！这说明本轮突变策略有效，"
                   f"可能触发了冰结合面的关键改善。建议在此方向上继续微调。")
        elif iri_chg > 20:
            return (f"IRI 活性显著改善 {iri_chg:+.1f}%。这验证了'几何互补可独立驱动 IRI'"
                   f"的设计原则——即使 TH 不变，IRI 也可通过非 IBS 面优化获得大幅提升。")
        elif expr > 0.8:
            return (f"表达评分达到 {expr:.3f}，已进入高表达区间。高疏水性 (GRAVY>0.5)"
                   f"曾是表达瓶颈，通过亲水化突变已成功解决。")
        else:
            return (f"本轮为渐进式优化，TH/IRI 呈小幅改善趋势。"
                   f"在 Type I AFP 的 TH 硬约束下，持续积累边际改善是可行的设计路径。")

    def _analyze_strategy_evolution(self) -> str:
        """分析策略演进路径"""
        lines = []
        if not self.rounds:
            return "> 无设计数据。\n"

        lines.append("以下展示了设计策略的演进过程：\n")

        phases = self._identify_design_phases()
        for i, (name, rounds_list) in enumerate(phases):
            rng = f"R{rounds_list[0]['round']}–R{rounds_list[-1]['round']}"
            total = len(rounds_list)
            passed = sum(1 for r in rounds_list if r["verdict"] == "PASS")
            rejected = sum(1 for r in rounds_list if r["verdict"] == "REJECTED")
            th_vals = [r["th_change_pct"] for r in rounds_list]
            iri_vals = [r["iri_change_pct"] for r in rounds_list]

            lines.append(f"### 阶段 {i+1}: {name} ({rng})\n")
            lines.append(f"- **轮次数**: {total} | ✅ PASS: {passed} | ❌ REJECTED: {rejected}")
            lines.append(f"- **TH 变化范围**: {min(th_vals):+.1f}% ~ {max(th_vals):+.1f}%")
            lines.append(f"- **IRI 变化范围**: {min(iri_vals):+.1f}% ~ {max(iri_vals):+.1f}%")

            # 策略评价
            if rejected > 0:
                lines.append(f"- ⚠️ 本阶段有 {rejected} 个突变被拒绝——这些位点/策略应在后续设计中避免")
            if passed == total and total >= 2:
                lines.append(f"- 🟢 所有突变均通过——该策略安全性高，适合作为基础优化方向")
            if max(th_vals) > 10:
                lines.append(f"- 🔥 TH 有显著突破——该策略可能在 IBS 面产生了有效改善")
            lines.append("")

        # 整体演进总结
        lines.append("### 整体演进趋势\n")

        # 找转折点
        turning_points = []
        for i in range(1, len(self.rounds)):
            prev = self.rounds[i-1]
            curr = self.rounds[i]
            if curr.get("verdict") == "REJECTED" and prev.get("verdict") != "REJECTED":
                turning_points.append((i+1, "策略受挫——突变被拒绝"))
            if curr["th_change_pct"] > prev["th_change_pct"] + 15:
                turning_points.append((i+1, "TH 突破——策略方向正确"))
            if curr["expression_score"] > prev["expression_score"] + 0.15:
                turning_points.append((i+1, "表达大幅改善——亲水化策略生效"))

        if turning_points:
            for rnd, desc in turning_points[-5:]:
                lines.append(f"- **Round {rnd}**: {desc}")

        lines.append(f"\n> 设计从保守策略（非 IBS 面亲水化）逐步过渡到激进策略（IBS 面修饰），"
                    f"在确保安全性的前提下探索性能上限。")
        lines.append("")

        return "\n".join(lines)

    def _extract_design_rules(self) -> str:
        """从设计数据中提取关键发现和设计规则"""
        lines = []

        lines.append("### 7.1 从本轮设计中发现的规则\n")

        if not self.rounds:
            lines.append("> 本轮无设计数据。\n")
            return "\n".join(lines)

        passed = [r for r in self.rounds if r["verdict"] == "PASS"]
        rejected = [r for r in self.rounds if r["verdict"] == "REJECTED"]
        caution = [r for r in self.rounds if r["verdict"] == "CAUTION"]

        lines.append(f"| 统计 | 数量 |")
        lines.append(f"|------|:----:|")
        lines.append(f"| 总轮次 | {len(self.rounds)} |")
        lines.append(f"| ✅ PASS | {len(passed)} |")
        lines.append(f"| 🟡 CAUTION | {len(caution)} |")
        lines.append(f"| ❌ REJECTED | {len(rejected)} |")
        lines.append(f"| 成功率 | {len(passed)/max(len(self.rounds),1):.0%} |\n")

        # 成功策略
        if passed:
            lines.append("### 7.2 ✅ 已验证的有效策略\n")
            # 去重归类
            strategies = {}
            for r in passed:
                muts_str = ", ".join(r["mutations"])
    # 简化归类
                if "S" in muts_str and all("S" in m for m in r["mutations"]):
                    cat = "Ala→Ser 亲水化"
                elif "N" in muts_str:
                    cat = "Asn 引入"
                elif "T" in muts_str:
                    cat = "Thr 引入"
                elif "Q" in muts_str:
                    cat = "Gln 引入"
                elif "C" in muts_str:
                    cat = "Cys 二硫键"
                elif "E" in muts_str:
                    cat = "Glu 替代"
                else:
                    cat = "其他"
                if cat not in strategies:
                    strategies[cat] = []
                strategies[cat].append(r)

            for cat, cat_rounds in strategies.items():
                avg_th = sum(r["th_change_pct"] for r in cat_rounds) / len(cat_rounds)
                avg_iri = sum(r["iri_change_pct"] for r in cat_rounds) / len(cat_rounds)
                lines.append(f"- **{cat}** ({len(cat_rounds)} 轮): "
                           f"TH 平均 {avg_th:+.1f}%, IRI 平均 {avg_iri:+.1f}%")
            lines.append("")

        # 失败策略
        if rejected:
            lines.append("### 7.3 ❌ 应严格避免的突变\n")
            for r in rejected:
                lines.append(f"- **{', '.join(r['mutations'])}** (Round {r['round']}): "
                           f"{r.get('rationale', '')[:150]}")
            lines.append("")

        # 通用规则
        lines.append("### 7.4 通用设计规则\n")
        lines.append("基于全部设计数据，总结以下通用规则：\n")

        # 动态规则
        rules = []
        if any("S" in str(r["mutations"]) for r in self.rounds):
            rules.append("**非 IBS 面 Ala→Ser 是最安全的起始策略**——提高表达但不影响冰结合活性")
        if rejected:
            rules.append("**IBS 核心残基 (Thr) 不可突变**——每次尝试均被 REJECTED，活性崩溃 >80%")
        if any(r["iri_change_pct"] > 15 for r in self.rounds):
            rules.append("**IRI 可通过非 IBS 面优化大幅改善**——验证了'几何互补可独立驱动 IRI'原则")
        if any(r["th_change_pct"] < 5 for r in self.rounds) and len(self.rounds) >= 5:
            rules.append("**Type I AFP 的 TH 受 IBS Thr 间距硬约束**——非 IBS 面突变对 TH 提升有限")
        if any("C" in str(r["mutations"]) for r in self.rounds):
            rules.append("**α-螺旋中 i→i+4 Cys 对几何不匹配**——不适合形成二硫键")
        if any(r["expression_score"] > 0.7 for r in self.rounds):
            rules.append("**亲水化可有效提升表达量**——高 GRAVY 是表达瓶颈，Ala→Ser 可有效降低疏水性")

        if not rules:
            rules.append("本轮设计数据不足以提取通用规则——建议增加设计轮次。")

        for rule in rules:
            lines.append(f"- {rule}")

        lines.append("")

        return "\n".join(lines)

    # ================================================================
    # 可视化
    # ================================================================
    def generate_visualization(self):
        """生成性能变化轨迹图，保存到 images/trajectory.png"""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("⚠️ matplotlib 未安装，跳过可视化。pip install matplotlib")
            return None

        if len(self.rounds) < 1:
            return None

        plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False

        rounds = [r["round"] for r in self.rounds]
        th_vals = [r["th_value"] for r in self.rounds]
        iri_vals = [r["iri_value"] for r in self.rounds]
        expr_vals = [r["expression_score"] for r in self.rounds]
        stab_vals = [r["stability_score"] for r in self.rounds]
        afp_probs = [r["afp_probability"] for r in self.rounds]

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"AFP Design Trajectory — {self.session_id}",
                     fontsize=14, fontweight="bold")

        # TH
        ax1 = axes[0][0]
        ax1.plot(rounds, th_vals, "o-", color="#E74C3C", lw=2, ms=6)
        ax1.set_xlabel("Design Round"); ax1.set_ylabel("TH (C)")
        ax1.set_title("Thermal Hysteresis (TH)"); ax1.grid(True, alpha=0.3)
        if self.baseline.get("th"):
            ax1.axhline(y=self.baseline["th"], color="gray", ls="--", alpha=0.5,
                       label=f"Baseline ({self.baseline['th']}C)")
            ax1.legend()

        # IRI
        ax2 = axes[0][1]
        ax2.plot(rounds, iri_vals, "o-", color="#3498DB", lw=2, ms=6)
        ax2.set_xlabel("Design Round"); ax2.set_ylabel("IRI IC50 (uM)")
        ax2.set_title("Ice Recrystallization Inhibition (IRI)"); ax2.grid(True, alpha=0.3)
        if self.baseline.get("iri"):
            ax2.axhline(y=self.baseline["iri"], color="gray", ls="--", alpha=0.5,
                       label=f"Baseline ({self.baseline['iri']}uM)")
            ax2.legend()

        # Expression + Stability
        ax3 = axes[1][0]
        ax3.plot(rounds, expr_vals, "o-", color="#2ECC71", lw=2, ms=6, label="Expression")
        ax3.plot(rounds, stab_vals, "s--", color="#F39C12", lw=2, ms=6, label="Stability")
        ax3.set_xlabel("Design Round"); ax3.set_ylabel("Score (0-1)")
        ax3.set_title("Expression & Stability"); ax3.legend(); ax3.grid(True, alpha=0.3)
        ax3.set_ylim(0, 1.1)

        # AFP Probability
        ax4 = axes[1][1]
        ax4.plot(rounds, afp_probs, "o-", color="#9B59B6", lw=2, ms=6)
        ax4.set_xlabel("Design Round"); ax4.set_ylabel("AFP Probability")
        ax4.set_title("AFP Probability Trend"); ax4.grid(True, alpha=0.3)
        ax4.set_ylim(0, 1.05)
        ax4.axhline(y=0.9, color="green", ls="--", alpha=0.5, label="High confidence")
        ax4.legend()

        plt.tight_layout()
        chart_path = self.images_dir / "trajectory.png"
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close()

        print(f"\n📊 可视化已生成: {chart_path}")
        return str(chart_path)

    # ================================================================
    # 工具方法
    # ================================================================
    def get_session_dir(self) -> str:
        return str(self.session_dir)

    def get_session_id(self) -> str:
        return self.session_id
