"""
技能存储系统 - 从突变经验中自动提炼设计技能

借鉴 Hermes Agent 的技能系统模式:
- 从多次实验中自动总结规律
- 生成 SKILL.md 格式的设计知识
- 持久化存储，跨会话使用
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class DesignSkill:
    """设计技能"""
    name: str                        # 技能名称
    description: str                 # 简短描述
    category: str                    # 分类: motif_mutation/region_design/property_tradeoff
    trigger_condition: str           # 何时触发此技能
    rules: List[str]                 # 设计规则列表
    examples: List[Dict]             # 成功案例
    counter_examples: List[Dict]     # 失败案例 (禁区)
    confidence: float                # 置信度 (0-1)
    evidence_count: int              # 证据数量
    created_at: float                # 创建时间
    updated_at: float                # 更新时间
    version: int = 1                 # 版本号


class SkillStore:
    """
    技能存储

    借鉴 Hermes 的 Curator 模式:
    - 自动从突变记忆中发现规律
    - 生成新的设计技能
    - 更新已有技能
    - 按置信度排序
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = Path(skills_dir) if skills_dir else \
            Path(__file__).parent.parent / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        self._skills: Dict[str, DesignSkill] = {}
        self._load()

    def _load(self):
        """从磁盘加载技能"""
        skills_file = self.skills_dir / "design_skills.json"
        if skills_file.exists():
            with open(skills_file, 'r') as f:
                data = json.load(f)
                for skill_data in data.get("skills", []):
                    skill = DesignSkill(**skill_data)
                    self._skills[skill.name] = skill

    def _save(self):
        """保存技能到磁盘"""
        skills_file = self.skills_dir / "design_skills.json"
        with open(skills_file, 'w') as f:
            json.dump({
                "skills": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "category": s.category,
                        "trigger_condition": s.trigger_condition,
                        "rules": s.rules,
                        "examples": s.examples,
                        "counter_examples": s.counter_examples,
                        "confidence": s.confidence,
                        "evidence_count": s.evidence_count,
                        "created_at": s.created_at,
                        "updated_at": s.updated_at,
                        "version": s.version,
                    }
                    for s in self._skills.values()
                ]
            }, f, indent=2, ensure_ascii=False)

    def add_or_update_skill(self, name: str, description: str,
                             category: str, trigger: str,
                             rules: List[str],
                             examples: List[Dict],
                             counter_examples: List[Dict],
                             evidence_count: int) -> DesignSkill:
        """添加或更新技能"""
        confidence = min(0.95, 0.3 + evidence_count * 0.05)

        if name in self._skills:
            # 更新已有技能
            skill = self._skills[name]
            skill.rules = list(set(skill.rules + rules))
            skill.examples.extend(examples)
            skill.counter_examples.extend(counter_examples)
            skill.evidence_count += evidence_count
            skill.confidence = min(0.95, 0.3 + skill.evidence_count * 0.05)
            skill.updated_at = time.time()
            skill.version += 1
        else:
            # 创建新技能
            skill = DesignSkill(
                name=name,
                description=description,
                category=category,
                trigger_condition=trigger,
                rules=rules,
                examples=examples[:10],
                counter_examples=counter_examples[:10],
                confidence=confidence,
                evidence_count=evidence_count,
                created_at=time.time(),
                updated_at=time.time(),
            )
            self._skills[name] = skill

        self._save()
        return skill

    def get_skill(self, name: str) -> Optional[DesignSkill]:
        """获取指定技能"""
        return self._skills.get(name)

    def get_skills_by_category(self, category: str) -> List[DesignSkill]:
        """按分类获取技能"""
        return [s for s in self._skills.values()
                if s.category == category]

    def get_high_confidence_skills(self, min_confidence: float = 0.5) -> List[DesignSkill]:
        """获取高置信度技能"""
        return [s for s in self._skills.values()
                if s.confidence >= min_confidence]

    def get_all_skills(self) -> List[DesignSkill]:
        """获取所有技能"""
        return sorted(self._skills.values(),
                     key=lambda s: s.confidence, reverse=True)

    def generate_skill_from_memory(self, memory) -> List[DesignSkill]:
        """
        从突变记忆自动生成设计技能

        分析模式:
        - 相同的氨基酸变化在不同上下文中反复成功 → 设计规则
        - 相同的氨基酸变化反复失败 → 禁区
        - 某个基序区域的突变总是带来相似效果 → 区域设计规则
        """
        new_skills = []

        successful = memory.get_successful_patterns()
        forbidden = memory.get_forbidden_zones()

        # 分析成功模式
        for aa_change, info in successful.items():
            if info["success_count"] >= 3:
                skill_name = f"mutation_{aa_change.replace('→','_to_')}"
                rules = [f"在合适的结构环境中, {aa_change}替换可改善抗冻蛋白性能"]
                examples = [{"change": aa_change, "note": n}
                          for n in info["examples"][:5]]

                skill = self.add_or_update_skill(
                    name=skill_name,
                    description=f"{aa_change}氨基酸替换的设计规则",
                    category="motif_mutation",
                    trigger=f"当设计目标涉及{aa_change}所影响的性质时",
                    rules=rules,
                    examples=examples,
                    counter_examples=[],
                    evidence_count=info["success_count"],
                )
                new_skills.append(skill)

        # 分析禁区
        for aa_change, info in forbidden.items():
            if info["failure_count"] >= 2:
                skill_name = f"avoid_{aa_change.replace('→','_to_')}"
                rules = [f"避免{aa_change}替换 - 已有{info['failure_count']}次失败记录"]

                skill = self.add_or_update_skill(
                    name=skill_name,
                    description=f"避免{aa_change}替换的警告",
                    category="motif_mutation",
                    trigger=f"当考虑{aa_change}突变时触发警告",
                    rules=rules,
                    examples=[],
                    counter_examples=[{"change": aa_change, "note": n}
                                    for n in info["examples"][:5]],
                    evidence_count=info["failure_count"],
                )
                new_skills.append(skill)

        return new_skills

    def get_skill_context_for_llm(self) -> str:
        """生成供LLM使用的技能上下文"""
        high_conf = self.get_high_confidence_skills(0.4)
        if not high_conf:
            return "暂无已确认的设计技能。"

        parts = ["## 抗冻蛋白设计技能库\n"]

        by_category = {}
        for skill in high_conf:
            cat = skill.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(skill)

        for cat, skills in by_category.items():
            cat_name = {"motif_mutation": "基序突变技能",
                       "region_design": "区域设计技能",
                       "property_tradeoff": "性质权衡技能"}.get(cat, cat)
            parts.append(f"\n### {cat_name}")

            for skill in sorted(skills, key=lambda s: s.confidence, reverse=True)[:5]:
                confidence_bar = "█" * int(skill.confidence * 10) + "░" * (10 - int(skill.confidence * 10))
                parts.append(f"\n#### {skill.name} (置信度: {confidence_bar} {skill.confidence:.0%})")
                parts.append(f"**触发条件**: {skill.trigger_condition}")
                parts.append(f"**规则**:")
                for rule in skill.rules[:5]:
                    parts.append(f"  - {rule}")

                if skill.examples:
                    parts.append(f"**成功案例** ({len(skill.examples)}个):")
                    for ex in skill.examples[:3]:
                        parts.append(f"  - {ex.get('note', str(ex))[:150]}")

                if skill.counter_examples:
                    parts.append(f"**失败案例/禁区** ({len(skill.counter_examples)}个):")
                    for ex in skill.counter_examples[:2]:
                        parts.append(f"  - ⚠️ {ex.get('note', str(ex))[:150]}")

        return "\n".join(parts)

    def export_skill_md(self, skill_name: str) -> Optional[str]:
        """导出单个技能为SKILL.md格式"""
        skill = self._skills.get(skill_name)
        if not skill:
            return None

        lines = [
            "---",
            f"name: {skill.name}",
            f"description: {skill.description}",
            f"version: {skill.version}.0.0",
            f"author: AFPAgent (auto-generated)",
            f"category: {skill.category}",
            "metadata:",
            "  afp_agent:",
            f"    confidence: {skill.confidence:.2f}",
            f"    evidence_count: {skill.evidence_count}",
            f"    created: {time.strftime('%Y-%m-%d', time.localtime(skill.created_at))}",
            "---",
            "",
            f"# {skill.name.replace('_', ' ').title()} Skill",
            "",
            "## When to Use",
            skill.trigger_condition,
            "",
            "## Design Rules",
        ]

        for i, rule in enumerate(skill.rules, 1):
            lines.append(f"{i}. {rule}")

        if skill.examples:
            lines.append("")
            lines.append("## Successful Examples")
            for i, ex in enumerate(skill.examples[:5], 1):
                lines.append(f"{i}. {ex.get('note', str(ex))}")

        if skill.counter_examples:
            lines.append("")
            lines.append("## Avoid (Counter-Examples)")
            for i, ex in enumerate(skill.counter_examples[:5], 1):
                lines.append(f"{i}. {ex.get('note', str(ex))}")

        return "\n".join(lines)
