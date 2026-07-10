# tools/memory_tools.py
"""
记忆管理工具集
包含：添加记忆、替换记忆、删除记忆、列出记忆
"""

import sys
import os

# 添加父目录(ch5/)到路径，以便导入 memory_store
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_store import MemoryStore
from .registry import tool_registry

# 创建全局记忆存储实例
memory_store = MemoryStore()


# ============================================================
# 工具1: add_memory - 添加记忆
# ============================================================

@tool_registry.tool(
    name="add_memory",
    description="向持久记忆中添内容。可添加到memory（环境事实、项目约定、经验教训）或user（用户偏好、沟通风格）。当用户透露了重要偏好、习惯或环境配置时使用。",
    content="string:要记录的记忆内容，应该简洁、明确",
    target="string:存储目标，可选 memory（个人笔记）或 user（用户画像）"
)
def add_memory_handler(content: str, target: str = "memory") -> dict:
    """添加记忆条目"""
    if target == "memory":
        return memory_store.add_memory(content)
    elif target == "user":
        return memory_store.add_user(content)
    else:
        return {"success": False, "error": f"未知的target: {target}，请使用 'memory' 或 'user'"}


# ============================================================
# 工具2: replace_memory - 替换记忆
# ============================================================

@tool_registry.tool(
    name="replace_memory",
    description="替换持久记忆中过时的条目。用子字符串匹配找到目标条目后替换为新内容。适用于纠正错误信息、更新过期配置。",
    old_text="string:要替换的旧内容（可子字符串匹配）",
    new_content="string:新内容",
    target="string:存储目标，可选 memory 或 user"
)
def replace_memory_handler(old_text: str, new_content: str, target: str = "memory") -> dict:
    """替换记忆条目"""
    if target == "memory":
        return memory_store.replace_memory(old_text, new_content)
    elif target == "user":
        return memory_store.replace_user(old_text, new_content)
    else:
        return {"success": False, "error": f"未知的target: {target}"}


# ============================================================
# 工具3: remove_memory - 删除记忆
# ============================================================

@tool_registry.tool(
    name="remove_memory",
    description="从持久记忆中删除过时的条目。用子字符串匹配找到要删除的条目并移除。适用于清理过时信息、删除错误记录。",
    old_text="string:要删除的记忆内容（可子字符串匹配）",
    target="string:存储目标，可选 memory 或 user"
)
def remove_memory_handler(old_text: str, target: str = "memory") -> dict:
    """删除记忆条目"""
    if target == "memory":
        return memory_store.remove_memory(old_text)
    elif target == "user":
        return memory_store.remove_user(old_text)
    else:
        return {"success": False, "error": f"未知的target: {target}"}


# ============================================================
# 工具4: list_memory - 列出所有记忆
# ============================================================

@tool_registry.tool(
    name="list_memory",
    description="列出当前所有的持久记忆条目。用于查看Agent记住了什么，帮助判断是否需要清理或补充。",
    target="string:可选，指定查看 memory 或 user，不指定则显示全部"
)
def list_memory_handler(target: str = "all") -> dict:
    """列出所有记忆"""
    entries = memory_store.list_entries()
    
    if target == "memory":
        return {"success": True, "target": "memory", **entries["memory"]}
    elif target == "user":
        return {"success": True, "target": "user", **entries["user"]}
    else:
        return {"success": True, **entries}


def register_all_tools():
    """注册所有记忆工具"""
    pass