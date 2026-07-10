"""
突变记忆系统 - 追踪每一次突变设计的结果

借鉴 Hermes Agent 的 memory_manager.py 模式:
- 持久化存储突变历史
- 按效果分类记忆
- 支持相似性查询
- 禁区自动标记
"""

import json
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class MutationRecord:
    """单次突变记录"""
    id: str                          # 唯一ID
    timestamp: float                 # 时间戳
    original_sequence: str           # 原始序列 (可截断)
    mutated_sequence: str            # 突变后序列 (可截断)
    mutations: List[Dict]            # 突变详情列表
    design_target: str               # 设计目标
    design_rationale: str            # LLM的设计理由

    # 评估结果
    evaluation_verdict: str          # pass/caution/warning/rejected
    evaluation_notes: List[str]      # 评估备注

    # 冰结合模拟结果
    th_change_pct: float = 0.0           # TH活性变化%
    iri_change_pct: float = 0.0          # IRI活性变化%
    geometry_change: float = 0.0         # 几何评分变化

    # 综合评分
    overall_score: float = 0.0           # -1.0 到 1.0
    is_successful: bool = False          # 是否成功
    tags: List[str] = field(default_factory=list)

    # 用于学习的特征
    aa_changes_summary: str = ""     # "A→G at pos 42" 的摘要
    motif_affected: str = ""         # 受影响的基序


class MutationMemory:
    """
    突变记忆系统

    核心功能:
    1. 记录每次突变设计及其结果
    2. 按氨基酸变化类型分类
    3. 识别成功/失败的模式
    4. 自动标记禁区 (重复失败的突变类型)
    5. 提供历史经验供LLM参考
    """

    def __init__(self, memory_dir: Optional[Path] = None):
        self.memory_dir = Path(memory_dir) if memory_dir else \
            Path(__file__).parent.parent / "data" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.records: List[MutationRecord] = []
        self._forbidden_zones: Dict[str, List[str]] = defaultdict(list)
        self._success_patterns: Dict[str, List[str]] = defaultdict(list)

        # 加载已有记忆
        self._load()

    def _load(self):
        """从磁盘加载记忆"""
        memory_file = self.memory_dir / "mutation_history.json"
        if memory_file.exists():
            with open(memory_file, 'r') as f:
                data = json.load(f)
                self.records = [
                    MutationRecord(**r) for r in data.get("records", [])
                ]
                self._rebuild_indices()

    def _save(self):
        """保存记忆到磁盘"""
        memory_file = self.memory_dir / "mutation_history.json"
        with open(memory_file, 'w') as f:
            json.dump({
                "records": [
                    {
                        "id": r.id,
                        "timestamp": r.timestamp,
                        "original_sequence": r.original_sequence[:200],
                        "mutated_sequence": r.mutated_sequence[:200],
                        "mutations": r.mutations,
                        "design_target": r.design_target,
                        "design_rationale": r.design_rationale[:500],
                        "evaluation_verdict": r.evaluation_verdict,
                        "evaluation_notes": r.evaluation_notes,
                        "th_change_pct": r.th_change_pct,
                        "iri_change_pct": r.iri_change_pct,
                        "geometry_change": r.geometry_change,
                        "overall_score": r.overall_score,
                        "is_successful": r.is_successful,
                        "tags": r.tags,
                        "aa_changes_summary": r.aa_changes_summary,
                        "motif_affected": r.motif_affected,
                    }
                    for r in self.records
                ]
            }, f, indent=2, ensure_ascii=False)

    def _rebuild_indices(self):
        """重建索引"""
        self._forbidden_zones.clear()
        self._success_patterns.clear()

        for record in self.records:
            if record.overall_score < -0.3:
                # 添加到禁区
                for mut in record.mutations:
                    key = f"{mut.get('from','')}→{mut.get('to','')}"
                    context = mut.get('context', '')
                    self._forbidden_zones[key].append(
                        f"在{context}环境中{key}导致性能下降"
                        f"(得分:{record.overall_score:.2f})"
                    )
            elif record.overall_score > 0.3:
                for mut in record.mutations:
                    key = f"{mut.get('from','')}→{mut.get('to','')}"
                    self._success_patterns[key].append(
                        f"成功案例: {key} 改善性能"
                        f"(得分:{record.overall_score:.2f})"
                    )

    def add_record(self, original_seq: str, mutated_seq: str,
                   mutations: List[Dict], design_target: str,
                   design_rationale: str,
                   evaluation_verdict: str,
                   evaluation_notes: List[str],
                   th_change: float = 0.0,
                   iri_change: float = 0.0,
                   geometry_change: float = 0.0) -> MutationRecord:
        """添加一条突变记录"""

        # 计算综合得分
        overall = self._calculate_overall_score(
            design_target, th_change, iri_change
        )

        # 生成氨基酸变化摘要
        aa_summary = ", ".join(
            f"{m.get('from','?')}→{m.get('to','?')}@{m.get('position','?')}"
            for m in mutations
        )

        # 识别受影响的基序
        motif = self._infer_motif_context(original_seq, mutations)

        record = MutationRecord(
            id=hashlib.md5(
                f"{original_seq[:50]}{mutated_seq[:50]}{time.time()}".encode()
            ).hexdigest()[:12],
            timestamp=time.time(),
            original_sequence=original_seq[:300],
            mutated_sequence=mutated_seq[:300],
            mutations=mutations,
            design_target=design_target,
            design_rationale=design_rationale[:500],
            evaluation_verdict=evaluation_verdict,
            evaluation_notes=evaluation_notes,
            th_change_pct=th_change,
            iri_change_pct=iri_change,
            geometry_change=geometry_change,
            overall_score=overall,
            is_successful=overall > 0.2,
            tags=self._generate_tags(mutations, design_target, overall),
            aa_changes_summary=aa_summary,
            motif_affected=motif,
        )

        self.records.append(record)
        self._rebuild_indices()
        self._save()

        return record

    def _calculate_overall_score(self, target: str, th_change: float,
                                   iri_change: float) -> float:
        """根据设计目标计算综合得分（AFP领域）"""
        target_lower = target.lower()

        # IRI improvement = negative iri_change (lower IC50 is better)
        iri_improvement = -iri_change

        if "th" in target_lower or "hysteresis" in target_lower:
            weights = {"th": 0.6, "iri": 0.4}
        elif "iri" in target_lower or "recrystallization" in target_lower:
            weights = {"th": 0.3, "iri": 0.7}
        else:
            weights = {"th": 0.5, "iri": 0.5}

        score = (th_change * weights["th"] + iri_improvement * weights["iri"]) / 50.0
        return max(-1.0, min(1.0, score))

    def _infer_motif_context(self, sequence: str,
                               mutations: List[Dict]) -> str:
        """推断突变影响的AFP基序"""
        seq = sequence.upper()
        motifs = []

        # AFP基序检测
        if 'TXT' in seq or 'TCT' in seq: motifs.append('TXT_motif')
        if 'NXT' in seq: motifs.append('NXT_motif')
        if seq.count('T') > len(seq) * 0.10: motifs.append('Thr_rich_IBS')
        if seq.count('A') > len(seq) * 0.40: motifs.append('Ala_rich_helix')
        if 'C' in seq and seq.count('C') >= 4: motifs.append('disulfide_scaffold')
        if seq.count('G') > len(seq) * 0.20: motifs.append('Gly_rich_loop')

        return ",".join(motifs[:3]) if motifs else "unknown"

    def _generate_tags(self, mutations: List[Dict], target: str,
                        score: float) -> List[str]:
        """生成标签"""
        tags = [target]

        for m in mutations:
            tags.append(f"{m.get('from','')}→{m.get('to','')}")

        if score > 0.5:
            tags.append("highly_successful")
        elif score > 0.2:
            tags.append("successful")
        elif score < -0.3:
            tags.append("harmful")

        return list(set(tags))

    def get_forbidden_zones(self) -> Dict:
        """获取禁区 - 不应该尝试的突变类型"""
        # 集中展示已失败至少2次的突变类型
        forbidden = {}
        for aa_change, notes in self._forbidden_zones.items():
            if len(notes) >= 2:
                forbidden[aa_change] = {
                    "mutation_type": aa_change,
                    "failure_count": len(notes),
                    "examples": notes[:3],
                }
        return forbidden

    def get_successful_patterns(self) -> Dict:
        """获取成功模式 - 值得尝试的突变类型"""
        successful = {}
        for aa_change, notes in self._success_patterns.items():
            if len(notes) >= 1:
                successful[aa_change] = {
                    "mutation_type": aa_change,
                    "success_count": len(notes),
                    "examples": notes[:3],
                }
        return successful

    def get_recent_records(self, n: int = 10) -> List[MutationRecord]:
        """获取最近的N条记录"""
        return sorted(self.records, key=lambda r: r.timestamp, reverse=True)[:n]

    def get_similar_mutations(self, aa_from: str, aa_to: str,
                                motif: str = None) -> List[MutationRecord]:
        """查找类似的突变记录"""
        similar = []
        for record in self.records:
            for mut in record.mutations:
                if (mut.get('from') == aa_from and
                    mut.get('to') == aa_to):
                    if motif is None or motif in record.motif_affected:
                        similar.append(record)
                        break
        return similar

    def get_memory_context_for_llm(self, target: str = None,
                                     max_items: int = 8) -> str:
        """
        生成供LLM使用的记忆上下文

        包含:
        - 最近的突变经验
        - 成功的模式
        - 需要避免的禁区
        """
        parts = ["## 突变设计历史记忆\n"]

        # 禁区警告
        forbidden = self.get_forbidden_zones()
        if forbidden:
            parts.append("### ⛔ 设计禁区 (已确认有害的突变类型)")
            for aa_change, info in list(forbidden.items())[:5]:
                parts.append(f"- **{aa_change}**: {info['failure_count']}次失败")
                for example in info["examples"][:2]:
                    parts.append(f"  - {example[:120]}")

        # 成功模式
        successful = self.get_successful_patterns()
        if successful:
            parts.append(f"\n### ✅ 成功模式 (值得尝试的突变类型)")
            for aa_change, info in list(successful.items())[:5]:
                parts.append(f"- **{aa_change}**: {info['success_count']}次成功")
                for example in info["examples"][:2]:
                    parts.append(f"  - {example[:120]}")

        # 最近记录
        recent = self.get_recent_records(max_items)
        if recent:
            parts.append(f"\n### 📝 最近的突变实验 (最近{len(recent)}次)")
            for i, r in enumerate(recent):
                emoji = "✅" if r.is_successful else "❌" if r.overall_score < -0.2 else "➡️"
                parts.append(
                    f"{i+1}. {emoji} {r.aa_changes_summary} "
                    f"[目标:{r.design_target}] "
                    f"[评分:{r.overall_score:+.2f}] "
                    f"[TH{r.th_change_pct:+.0f}% "
                    f"IRI{r.iri_change_pct:+.0f}%]"
                )
                if r.design_rationale:
                    parts.append(f"   理由: {r.design_rationale[:150]}")

        # 统计
        total = len(self.records)
        if total > 0:
            success_count = sum(1 for r in self.records if r.is_successful)
            parts.append(f"\n### 📈 统计")
            parts.append(f"- 总实验次数: {total}")
            parts.append(f"- 成功率: {success_count}/{total} "
                        f"({success_count/total*100:.0f}%)")
            if target:
                target_records = [r for r in self.records
                                if target in r.design_target.lower()]
                if target_records:
                    target_success = sum(1 for r in target_records
                                       if r.is_successful)
                    parts.append(f"- [{target}]目标成功率: "
                               f"{target_success}/{len(target_records)}")

        return "\n".join(parts)

    def get_stats(self) -> Dict:
        """获取记忆统计"""
        total = len(self.records)
        if total == 0:
            return {"total_experiments": 0}

        successful = sum(1 for r in self.records if r.is_successful)
        forbidden_count = len(self.get_forbidden_zones())

        # 按目标分类
        by_target = defaultdict(int)
        for r in self.records:
            by_target[r.design_target] += 1

        # 氨基酸变化频次
        aa_change_freq = defaultdict(lambda: {"success": 0, "failure": 0})
        for r in self.records:
            for mut in r.mutations:
                key = f"{mut.get('from','?')}→{mut.get('to','?')}"
                if r.is_successful:
                    aa_change_freq[key]["success"] += 1
                else:
                    aa_change_freq[key]["failure"] += 1

        return {
            "total_experiments": total,
            "success_count": successful,
            "success_rate": round(successful / total * 100, 1),
            "forbidden_zones_count": forbidden_count,
            "success_patterns_count": len(self.get_successful_patterns()),
            "experiments_by_target": dict(by_target),
            "top_mutations": sorted(
                [
                    {"change": k, "success": v["success"], "failure": v["failure"]}
                    for k, v in aa_change_freq.items()
                ],
                key=lambda x: x["success"] + x["failure"],
                reverse=True
            )[:10],
            "best_changes": sorted(
                [
                    {"change": k, "score": v["success"] - v["failure"]}
                    for k, v in aa_change_freq.items()
                    if v["success"] + v["failure"] >= 2
                ],
                key=lambda x: x["score"],
                reverse=True
            )[:5],
        }
