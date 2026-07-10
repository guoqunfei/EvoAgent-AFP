# skill_store.py
"""
技能存储模块
管理技能的生命周期：创建、读取、更新、删除、列出
支持技能复用与自我改进：使用追踪、过时检测、模糊匹配patch、健康评分
"""

import os
import json
import yaml
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class SkillStore:
    """
    技能存储类

    管理 ~/.hermes/skills/ 目录下的技能文件
    每个技能是一个目录，包含 SKILL.md 文件

    技能生命周期管理：
    - 基础CRUD：create, read, update, delete, list
    - 使用追踪：track_usage, set_outdated, get_outdated_skills
    - 技能匹配：match_skills, get_skills_for_matching, get_skill_metadata
    - 精准修复：patch (增强版模糊匹配), _fuzzy_patch, _record_patch_history
    - 健康评分：get_skill_health
    """

    def __init__(self, skills_root: str = "./skills"):
        """
        初始化技能存储

        参数:
            skills_root: 技能根目录路径
        """
        self.skills_root = Path(skills_root)
        self.skills_root.mkdir(parents=True, exist_ok=True)

        # 技能追踪数据文件
        self.tracking_file = self.skills_root.parent / ".skill_tracking.json"
        self._init_tracking()

    # ============================================================
    # 追踪数据管理
    # ============================================================

    def _init_tracking(self):
        """初始化技能追踪数据"""
        if not self.tracking_file.exists():
            self._save_tracking({"skills": {}})

    def _load_tracking(self) -> Dict:
        """加载技能追踪数据"""
        if self.tracking_file.exists():
            with open(self.tracking_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"skills": {}}

    def _save_tracking(self, data: Dict):
        """保存技能追踪数据"""
        with open(self.tracking_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ============================================================
    # 基础路径与解析工具
    # ============================================================

    def _skill_path(self, skill_name: str) -> Path:
        """获取技能的目录路径"""
        return self.skills_root / skill_name

    def _skill_file_path(self, skill_name: str) -> Path:
        """获取 SKILL.md 文件的完整路径"""
        return self._skill_path(skill_name) / "SKILL.md"

    def _validate_yaml_frontmatter(self, frontmatter: Dict) -> tuple:
        """
        验证 YAML frontmatter 的必需字段

        Hermes 要求 name 和 description 为必需字段
        """
        if "name" not in frontmatter:
            return False, "缺少必需字段: name"
        if "description" not in frontmatter:
            return False, "缺少必需字段: description"

        name = frontmatter["name"]
        if len(name) > 64:
            return False, f"技能名称过长: {len(name)} > 64 字符"

        desc = frontmatter["description"]
        if len(desc) > 1024:
            return False, f"技能描述过长: {len(desc)} > 1024 字符"

        return True, None

    def _parse_skill_md(self, content: str) -> tuple:
        """
        解析 SKILL.md 文件，提取 YAML frontmatter 和 Markdown 正文

        标准格式以 '---' 开始和结束 YAML frontmatter
        """
        lines = content.split("\n")

        if not lines or lines[0].strip() != "---":
            # 没有 frontmatter，返回空 frontmatter
            return {}, content

        # 找到 frontmatter 的结束位置
        end_index = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_index = i
                break

        if end_index == -1:
            return {}, content

        # 提取 YAML 部分
        yaml_content = "\n".join(lines[1:end_index])
        # 提取 Markdown 正文
        markdown_content = "\n".join(lines[end_index + 1:])

        try:
            frontmatter = yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError:
            frontmatter = {}

        return frontmatter, markdown_content

    def _build_skill_md(self, frontmatter: Dict, content: str) -> str:
        """构建完整的 SKILL.md 文件内容"""
        yaml_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
        return f"---\n{yaml_str}---\n{content}"

    # ============================================================
    # 基础 CRUD 操作
    # ============================================================

    def create(self, skill_name: str, frontmatter: Dict, content: str) -> Dict:
        """
        创建新技能

        参数:
            skill_name: 技能名称（将作为目录名）
            frontmatter: YAML frontmatter（包含 name, description 等）
            content: Markdown 正文（操作步骤、陷阱、验证方法等）

        返回:
            操作结果字典
        """
        # 验证 frontmatter
        valid, error = self._validate_yaml_frontmatter(frontmatter)
        if not valid:
            return {"success": False, "error": error}

        # 确保技能目录不存在
        skill_dir = self._skill_path(skill_name)
        if skill_dir.exists():
            return {"success": False, "error": f"技能 '{skill_name}' 已存在"}

        # 创建目录和文件
        try:
            skill_dir.mkdir(parents=True)
            skill_file_path = skill_dir / "SKILL.md"
            file_content = self._build_skill_md(frontmatter, content)

            with open(skill_file_path, "w", encoding="utf-8") as f:
                f.write(file_content)

            return {
                "success": True,
                "message": f"技能 '{skill_name}' 创建成功",
                "path": str(skill_file_path)
            }

        except Exception as e:
            return {"success": False, "error": f"创建失败: {str(e)}"}

    def read(self, skill_name: str) -> Dict:
        """
        读取技能完整内容

        参数:
            skill_name: 技能名称

        返回:
            包含 frontmatter 和 content 的字典
        """
        skill_file = self._skill_file_path(skill_name)

        if not skill_file.exists():
            return {"success": False, "error": f"技能 '{skill_name}' 不存在"}

        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()

            frontmatter, markdown = self._parse_skill_md(content)

            return {
                "success": True,
                "skill_name": skill_name,
                "frontmatter": frontmatter,
                "content": markdown,
                "full_content": content
            }

        except Exception as e:
            return {"success": False, "error": f"读取失败: {str(e)}"}

    def update(self, skill_name: str, frontmatter: Dict, content: str) -> Dict:
        """
        完全替换技能

        参数:
            skill_name: 技能名称
            frontmatter: 新的 YAML frontmatter
            content: 新的 Markdown 正文
        """
        valid, error = self._validate_yaml_frontmatter(frontmatter)
        if not valid:
            return {"success": False, "error": error}

        skill_file = self._skill_file_path(skill_name)

        if not skill_file.exists():
            return {"success": False, "error": f"技能 '{skill_name}' 不存在"}

        try:
            file_content = self._build_skill_md(frontmatter, content)

            with open(skill_file, "w", encoding="utf-8") as f:
                f.write(file_content)

            return {
                "success": True,
                "message": f"技能 '{skill_name}' 更新成功"
            }

        except Exception as e:
            return {"success": False, "error": f"更新失败: {str(e)}"}

    def delete(self, skill_name: str) -> Dict:
        """
        删除指定技能

        参数:
            skill_name: 技能名称
        """
        skill_dir = self._skill_path(skill_name)

        if not skill_dir.exists():
            return {"success": False, "error": f"技能 '{skill_name}' 不存在"}

        try:
            shutil.rmtree(skill_dir)
            return {
                "success": True,
                "message": f"技能 '{skill_name}' 已删除"
            }

        except Exception as e:
            return {"success": False, "error": f"删除失败: {str(e)}"}

    def list_skills(self) -> List[Dict]:
        """
        列出所有可用技能
        """
        skills = []

        for skill_dir in self.skills_root.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                with open(skill_file, "r", encoding="utf-8") as f:
                    content = f.read()

                frontmatter, _ = self._parse_skill_md(content)

                skills.append({
                    "name": skill_dir.name,
                    "display_name": frontmatter.get("name", skill_dir.name),
                    "description": frontmatter.get("description", ""),
                    "version": frontmatter.get("version", "1.0.0"),
                    "has_skill_file": True
                })

            except Exception as e:
                skills.append({
                    "name": skill_dir.name,
                    "display_name": skill_dir.name,
                    "description": f"[解析错误: {e}]",
                    "has_skill_file": True
                })

        return skills

    def get_stats(self) -> Dict:
        """
        获取技能统计信息
        """
        skills = self.list_skills()

        return {
            "total_skills": len(skills),
            "skills_root": str(self.skills_root),
            "skills": skills
        }

    # ============================================================
    # 技能使用追踪（ch8 新增：技能复用与自我改进）
    # ============================================================

    def track_usage(self, skill_name: str, result: str) -> Dict:
        """
        记录技能的使用情况

        参数:
            skill_name: 技能名称
            result: 使用结果（"success", "partial", "failed"）

        返回:
            更新后的统计信息
        """
        tracking = self._load_tracking()

        if skill_name not in tracking["skills"]:
            tracking["skills"][skill_name] = {
                "usage_count": 0,
                "success_count": 0,
                "partial_count": 0,
                "failed_count": 0,
                "last_used": None,
                "last_outdated_score": None
            }

        skill_stats = tracking["skills"][skill_name]
        skill_stats["usage_count"] += 1
        skill_stats["last_used"] = datetime.now().isoformat()

        if result == "success":
            skill_stats["success_count"] += 1
        elif result == "partial":
            skill_stats["partial_count"] += 1
        elif result == "failed":
            skill_stats["failed_count"] += 1

        # 计算成功率并判断是否过时
        success_rate = skill_stats["success_count"] / max(skill_stats["usage_count"], 1)

        # 如果成功率低于70%且使用次数超过3次，标记为过时
        if skill_stats["usage_count"] >= 3 and success_rate < 0.7:
            skill_stats["is_outdated"] = True
            skill_stats["last_outdated_score"] = success_rate
        else:
            skill_stats["is_outdated"] = False

        self._save_tracking(tracking)

        return {
            "usage_count": skill_stats["usage_count"],
            "success_rate": success_rate,
            "is_outdated": skill_stats.get("is_outdated", False)
        }

    def set_outdated(self, skill_name: str, reason: str) -> Dict:
        """
        标记技能为过时（供Agent主动标记）
        """
        tracking = self._load_tracking()

        if skill_name not in tracking["skills"]:
            tracking["skills"][skill_name] = {
                "usage_count": 0,
                "success_count": 0,
                "failed_count": 0,
                "last_used": None
            }

        tracking["skills"][skill_name]["is_outdated"] = True
        tracking["skills"][skill_name]["outdated_reason"] = reason
        tracking["skills"][skill_name]["last_outdated_time"] = datetime.now().isoformat()

        self._save_tracking(tracking)

        return {"success": True, "skill_name": skill_name, "marked_outdated": True}

    def get_outdated_skills(self) -> List[Dict]:
        """获取所有被标记为过时的技能"""
        tracking = self._load_tracking()
        outdated = []

        for skill_name, stats in tracking["skills"].items():
            if stats.get("is_outdated", False):
                # 读取技能元数据
                metadata = self.get_skill_metadata(skill_name)
                outdated.append({
                    "name": skill_name,
                    "usage_count": stats.get("usage_count", 0),
                    "success_rate": stats.get("success_count", 0) / max(stats.get("usage_count", 0), 1),
                    "outdated_reason": stats.get("outdated_reason", "基于成功率的自动检测"),
                    "display_name": metadata.get("display_name", skill_name),
                    "description": metadata.get("description", "")
                })

        return outdated

    # ============================================================
    # 技能元数据与匹配（ch8 新增：技能自动加载与匹配策略）
    # ============================================================

    def get_skill_metadata(self, skill_name: str) -> Dict:
        """获取技能的元数据（用于匹配）"""
        skill_file = self._skill_file_path(skill_name)

        if not skill_file.exists():
            return {}

        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()

        frontmatter, _ = self._parse_skill_md(content)
        return {
            "name": skill_name,
            "display_name": frontmatter.get("name", skill_name),
            "description": frontmatter.get("description", ""),
            "version": frontmatter.get("version", "1.0.0"),
            "tags": frontmatter.get("metadata", {}).get("hermes", {}).get("tags", [])
        }

    def get_skills_for_matching(self) -> List[Dict]:
        """
        获取所有技能的摘要元数据（用于System Prompt预加载）

        Hermes采用"渐进式披露"策略：
        - 技能元数据（name+description）预加载到System Prompt
        - 详细步骤在Agent需要时才按需读取
        """
        skills = self.list_skills()
        matching_list = []

        for skill in skills:
            metadata = self.get_skill_metadata(skill["name"])
            matching_list.append({
                "name": skill["name"],
                "display_name": metadata.get("display_name", skill["name"]),
                "description": metadata.get("description", ""),
                "tags": metadata.get("tags", [])
            })

        return matching_list

    def match_skills(self, task_description: str, limit: int = 3) -> List[Dict]:
        """
        根据任务描述匹配最相关的技能（基于关键词）

        Hermes中这一步由LLM自主完成——模型看到System Prompt中的技能列表，
        自主判断用户任务是否匹配某个技能。此方法作为备用关键词匹配。

        参数:
            task_description: 用户的任务描述
            limit: 返回的最大匹配数

        返回:
            按匹配分数排序的技能列表
        """
        # 获取所有技能的元数据
        skills_metadata = self.get_skills_for_matching()

        # 提取任务描述中的关键词（简化版：分词）
        keywords = set(task_description.lower().split())

        # 移除常见的停用词
        stop_words = {"的", "了", "是", "在", "我", "你", "他", "她", "它", "们",
                      "a", "an", "the", "to", "for", "of", "and", "with", "from", "this"}
        keywords = {word for word in keywords if word not in stop_words}

        if not keywords:
            return []

        scored_skills = []

        for skill in skills_metadata:
            score = 0

            # 匹配技能显示名称
            display_name_lower = skill["display_name"].lower()
            for keyword in keywords:
                if keyword in display_name_lower:
                    score += 3  # 名称匹配权重高

            # 匹配描述
            desc_lower = skill["description"].lower()
            for keyword in keywords:
                if keyword in desc_lower:
                    score += 1

            # 匹配标签
            tags_lower = " ".join(skill.get("tags", [])).lower()
            for keyword in keywords:
                if keyword in tags_lower:
                    score += 2

            if score > 0:
                scored_skills.append({
                    "skill_name": skill["name"],
                    "display_name": skill["display_name"],
                    "description": skill["description"],
                    "match_score": score
                })

        # 按分数排序
        scored_skills.sort(key=lambda x: x["match_score"], reverse=True)

        return scored_skills[:limit]

    # ============================================================
    # 技能自我改进：patch 精准修复（ch8 增强版：支持模糊匹配）
    # ============================================================

    def patch(self, skill_name: str, old_text: str, new_text: str, section: str = "auto") -> Dict:
        """
        精准修改技能中的特定段落（增强版：支持模糊匹配）

        Hermes的patch采用语义相似度的模糊行级替换机制：
        - 先尝试精确匹配替换
        - 精确匹配失败时，使用关键词模糊定位后替换
        - 即使存在轻微格式差异也能成功修改

        参数:
            skill_name: 技能名称
            old_text: 要替换的旧文本
            new_text: 新文本
            section: 修改区域（"frontmatter", "content", "auto"）
        """
        skill_file = self._skill_file_path(skill_name)

        if not skill_file.exists():
            return {"success": False, "error": f"技能 '{skill_name}' 不存在"}

        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                original_content = f.read()

            frontmatter, markdown = self._parse_skill_md(original_content)

            if section == "frontmatter":
                # frontmatter 的 patch 需要重新构建
                return {"success": False, "error": "patch frontmatter 暂未实现，请使用 update 操作"}

            elif section == "content":
                # 先尝试精确替换
                if old_text in markdown:
                    new_markdown = markdown.replace(old_text, new_text)
                else:
                    # 模糊匹配：使用关键词定位
                    new_markdown = self._fuzzy_patch(markdown, old_text, new_text)
                    if new_markdown == markdown:
                        return {"success": False, "error": f"未在正文中找到匹配文本: '{old_text[:80]}...'"}

                new_content = self._build_skill_md(frontmatter, new_markdown)

                # 记录patch历史
                self._record_patch_history(skill_name, old_text, new_text)

                with open(skill_file, "w", encoding="utf-8") as f:
                    f.write(new_content)

                return {
                    "success": True,
                    "message": f"技能 '{skill_name}' 补丁应用成功",
                    "section": section
                }

            else:  # auto — 尝试在完整内容中替换
                if old_text in original_content:
                    new_content = original_content.replace(old_text, new_text)
                else:
                    # 模糊匹配
                    _, body = self._parse_skill_md(original_content)
                    new_body = self._fuzzy_patch(body, old_text, new_text)
                    if new_body == body:
                        return {"success": False, "error": f"未在技能中找到匹配文本: '{old_text[:80]}...'"}
                    new_content = self._build_skill_md(frontmatter, new_body)

                self._record_patch_history(skill_name, old_text, new_text)

                with open(skill_file, "w", encoding="utf-8") as f:
                    f.write(new_content)

                return {
                    "success": True,
                    "message": f"技能 '{skill_name}' 补丁应用成功",
                    "section": section
                }

        except Exception as e:
            return {"success": False, "error": f"打补丁失败: {str(e)}"}

    def _fuzzy_patch(self, content: str, old_text: str, new_text: str) -> str:
        """
        模糊匹配替换（基于关键词分组）

        当精确匹配失败时，提取old_text的关键词，
        在content中定位包含这些关键词的行，然后替换。
        """
        # 提取old_text中的关键词
        keywords = set(old_text.lower().split())
        keywords = {kw for kw in keywords
                    if len(kw) >= 3
                    and kw not in ["the", "and", "for", "with", "from", "this"]}

        if not keywords:
            return content

        lines = content.split("\n")
        matched_indices = []

        for i, line in enumerate(lines):
            line_lower = line.lower()
            for kw in keywords:
                if kw in line_lower:
                    matched_indices.append(i)
                    break

        if not matched_indices:
            return content

        # 选择第一个匹配行作为替换目标
        target_idx = matched_indices[0]

        # 替换该行内容
        lines[target_idx] = new_text

        return "\n".join(lines)

    def _record_patch_history(self, skill_name: str, old_text: str, new_text: str):
        """记录patch历史，用于技能优化追踪"""
        tracking = self._load_tracking()

        if skill_name not in tracking["skills"]:
            tracking["skills"][skill_name] = {}

        if "patch_history" not in tracking["skills"][skill_name]:
            tracking["skills"][skill_name]["patch_history"] = []

        tracking["skills"][skill_name]["patch_history"].append({
            "timestamp": datetime.now().isoformat(),
            "old_text_preview": old_text[:100],
            "new_text_preview": new_text[:100],
            "version_increment": 1
        })

        self._save_tracking(tracking)

    # ============================================================
    # 技能健康评分（ch8 新增：使用统计与效果评分）
    # ============================================================

    def get_skill_health(self, skill_name: str) -> Dict:
        """
        获取技能的运行状况评分

        返回:
            health_status: "healthy", "needs_review", "needs_patch", "deprecated", "unused"
            health_score: 0-100 的综合健康评分
        """
        tracking = self._load_tracking()

        if skill_name not in tracking["skills"]:
            skill_stats = {"usage_count": 0, "success_count": 0, "failed_count": 0}
        else:
            skill_stats = tracking["skills"][skill_name]

        usage = skill_stats.get("usage_count", 0)
        success_count = skill_stats.get("success_count", 0)
        failed_count = skill_stats.get("failed_count", 0)
        last_used = skill_stats.get("last_used")
        is_outdated = skill_stats.get("is_outdated", False)

        if usage == 0:
            return {
                "health_status": "unused",
                "health_score": 50,
                "usage_count": 0,
                "success_rate": 0.0,
                "message": "技能尚未使用过"
            }

        # 根据成功率和使用频率计算健康评分
        success_rate = success_count / usage if usage > 0 else 0
        failed_rate = failed_count / usage if usage > 0 else 0

        # 健康评分公式：成功率权重40% + 无失败率权重40% + 活跃度权重20%
        health_score = (success_rate * 40) + ((1 - failed_rate) * 40) + min(usage / 10, 1.0) * 20

        if is_outdated or health_score < 50:
            health_status = "needs_patch"
        elif health_score < 70:
            health_status = "needs_review"
        elif health_score >= 70:
            health_status = "healthy"

        # 检查最近使用时间（超过30天未使用）
        if last_used:
            last_date = datetime.fromisoformat(last_used)
            if (datetime.now() - last_date).days > 30:
                health_status = "deprecated"
                health_score = max(health_score - 20, 0)

        return {
            "health_status": health_status,
            "health_score": round(health_score, 1),
            "usage_count": usage,
            "success_rate": round(success_rate, 2),
            "message": self._get_health_message(health_status)
        }

    def _get_health_message(self, status: str) -> str:
        """返回健康状态的友好说明"""
        messages = {
            "healthy": "技能运行良好，可以继续使用",
            "needs_review": "技能出现了部分问题，建议审查流程",
            "needs_patch": "技能失败率较高，建议使用patch修复",
            "deprecated": "技能长时间未使用，可能已过时",
            "unused": "技能尚未被使用过，请测试验证"
        }
        return messages.get(status, "状态未知")


# 创建全局单例
skill_store = SkillStore()
