# tools/skill_tools.py
"""
技能管理工具集
包含：create, read, update, patch, delete, list 六个操作
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_store import skill_store
from .registry import tool_registry


# ============================================================
# skill_manage 主工具：统一入口
# ============================================================

@tool_registry.tool(
    name="skill_manage",
    description="""管理Agent的技能库。支持以下操作：
- create: 创建新技能。需要提供技能名称、YAML frontmatter（至少包含name和description）和Markdown内容
- read: 读取技能完整内容
- update: 完全替换一个已有技能
- patch: 精准修改技能中的特定段落（模糊匹配替换）
- delete: 删除一个技能
- list: 列出所有可用技能

技能是Agent的程序性记忆——捕获"如何做某类特定任务"的具体步骤，包括操作步骤、常见陷阱和验证方法。""",
    action="string:操作类型：create, read, update, patch, delete, list",
    skill_name="string:技能名称（create/read/update/patch/delete时使用）",
    frontmatter="string:YAML frontmatter的JSON字符串，包含name和description（create/update时使用）",
    content="string:Markdown正文（create/update时使用）",
    old_text="string:要替换的旧文本（patch时使用）",
    new_text="string:新文本（patch时使用）",
    section="string:patch区域：frontmatter/content/auto（默认auto）"
)
def skill_manage_handler(
    action: str,
    skill_name: str = "",
    frontmatter: str = "",
    content: str = "",
    old_text: str = "",
    new_text: str = "",
    section: str = "auto"
) -> dict:
    """
    技能管理统一入口
    """
    
    # ============ LIST 操作 ============
    if action == "list":
        stats = skill_store.get_stats()
        
        if stats["total_skills"] == 0:
            return {
                "success": True,
                "action": "list",
                "message": "技能库为空。完成复杂任务后，使用 create 操作创建技能。",
                "skills": [],
                "count": 0
            }
        
        return {
            "success": True,
            "action": "list",
            "skills": stats["skills"],
            "count": stats["total_skills"]
        }
    
    # ============ CREATE 操作 ============
    if action == "create":
        if not skill_name:
            return {"success": False, "action": "create", "error": "技能名称不能为空"}
        if not frontmatter:
            return {"success": False, "action": "create", "error": "frontmatter 不能为空"}

        try:
            import json
            frontmatter_dict = json.loads(frontmatter)
        except json.JSONDecodeError:
            return {"success": False, "action": "create", "error": "frontmatter 必须是有效的 JSON 字符串"}

        result = skill_store.create(skill_name, frontmatter_dict, content or "")
        result["action"] = "create"
        return result

    # ============ READ 操作 ============
    if action == "read":
        if not skill_name:
            return {"success": False, "action": "read", "error": "技能名称不能为空"}

        result = skill_store.read(skill_name)
        result["action"] = "read"
        return result

    # ============ UPDATE 操作 ============
    if action == "update":
        if not skill_name:
            return {"success": False, "action": "update", "error": "技能名称不能为空"}
        if not frontmatter:
            return {"success": False, "action": "update", "error": "frontmatter 不能为空"}

        try:
            import json
            frontmatter_dict = json.loads(frontmatter)
        except json.JSONDecodeError:
            return {"success": False, "action": "update", "error": "frontmatter 必须是有效的 JSON 字符串"}

        result = skill_store.update(skill_name, frontmatter_dict, content or "")
        result["action"] = "update"
        return result

    # ============ PATCH 操作 ============
    if action == "patch":
        if not skill_name:
            return {"success": False, "action": "patch", "error": "技能名称不能为空"}
        if not old_text:
            return {"success": False, "action": "patch", "error": "old_text 不能为空"}
        if not new_text:
            return {"success": False, "action": "patch", "error": "new_text 不能为空"}

        result = skill_store.patch(skill_name, old_text, new_text, section)
        result["action"] = "patch"
        return result

    # ============ DELETE 操作 ============
    if action == "delete":
        if not skill_name:
            return {"success": False, "action": "delete", "error": "技能名称不能为空"}

        result = skill_store.delete(skill_name)
        result["action"] = "delete"
        return result
    
    # ============ 未知操作 ============
    return {
        "success": False,
        "action": "unknown",
        "error": f"未知操作: {action}。支持的操作: create, read, update, patch, delete, list"
    }


def register_all_tools():
    """注册所有技能工具"""
    pass


# ============================================================
# track_skill_usage 工具：记录技能使用情况
# ============================================================

@tool_registry.tool(
    name="track_skill_usage",
    description="""记录技能的使用结果。Agent在调用技能执行任务后，根据验证结果调用此工具记录使用情况。

系统会根据使用统计自动判断技能是否过时：
- 使用次数≥3且成功率<70%时，自动标记为过时
- 标记过时的技能会在技能列表中显示警告""",
    skill_name="string:技能名称（必填）",
    result="string:使用结果，可选值 success/partial/failed（必填）"
)
def track_skill_usage_handler(skill_name: str, result: str) -> dict:
    """
    记录技能使用情况

    参数:
        skill_name: 技能名称
        result: 使用结果 ("success", "partial", "failed")
    """
    if result not in ("success", "partial", "failed"):
        return {
            "success": False,
            "error": f"无效的result值: '{result}'。可选: success, partial, failed"
        }

    tracking_result = skill_store.track_usage(skill_name, result)

    return {
        "success": True,
        "message": f"技能 '{skill_name}' 使用记录已更新",
        "usage_count": tracking_result["usage_count"],
        "success_rate": tracking_result["success_rate"],
        "is_outdated": tracking_result["is_outdated"]
    }


# ============================================================
# get_skill_health 工具：查看技能健康状态
# ============================================================

@tool_registry.tool(
    name="get_skill_health",
    description="""查看指定技能的运行状况评分。返回健康状态、评分和使用统计。

健康状态说明：
- healthy: 运行良好 (≥70分)
- needs_review: 需要审查 (50-69分)
- needs_patch: 需要修复 (<50分或已标记过时)
- deprecated: 长时间未使用
- unused: 尚未使用过""",
    skill_name="string:技能名称（必填）"
)
def get_skill_health_handler(skill_name: str) -> dict:
    """
    获取技能健康状态
    """
    health = skill_store.get_skill_health(skill_name)

    if health["health_status"] == "unused" and health["usage_count"] == 0:
        # 检查技能是否存在
        skill_data = skill_store.read(skill_name)
        if not skill_data.get("success"):
            return {"success": False, "error": f"技能 '{skill_name}' 不存在"}

    return {
        "success": True,
        "skill_name": skill_name,
        **health
    }


# ============================================================
# mark_skill_outdated 工具：手动标记技能过时
# ============================================================

@tool_registry.tool(
    name="mark_skill_outdated",
    description="""手动标记技能为过时。Agent在执行技能后发现步骤已完全失效，可主动标记。

这与系统自动检测（成功率<70%）互补——Agent可以基于语义理解提前发现过时问题。""",
    skill_name="string:技能名称（必填）",
    reason="string:过时原因（必填），例如'API端点已变更'、'依赖包已废弃'"
)
def mark_skill_outdated_handler(skill_name: str, reason: str) -> dict:
    """
    手动标记技能为过时
    """
    result = skill_store.set_outdated(skill_name, reason)
    return result