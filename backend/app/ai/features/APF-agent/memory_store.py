# memory_store.py
"""
记忆存储模块
管理 MEMORY.md 和 USER.md 的读写和容量控制
"""

import os
import json
import re
from typing import List, Dict, Optional
from pathlib import Path


class MemoryStore:
    """
    记忆存储类（简化版，使用JSON格式）
    
    Hermes原版使用 Markdown + § 分隔符，本讲使用 JSON 格式便于理解。
    后续可以扩展支持 Markdown 格式。
    """
    
    def __init__(
        self,
        memory_path: str = "./memories/MEMORY.json",
        user_path: str = "./memories/USER.json",
        memory_char_limit: int = 2200,   # MEMORY.md 字符限制
        user_char_limit: int = 1375      # USER.md 字符限制
    ):
        """
        初始化记忆存储
        
        参数:
            memory_path: MEMORY 文件路径（Agent个人笔记）
            user_path: USER 文件路径（用户画像）
            memory_char_limit: MEMORY 最大字符数（默认2200）
            user_char_limit: USER 最大字符数（默认1375）
        """
        self.memory_path = Path(memory_path)
        self.user_path = Path(user_path)
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit
        
        # 内存中的条目列表
        self.memory_entries: List[str] = []
        self.user_entries: List[str] = []
        
        # 确保目录存在
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载已有的记忆
        self._load()
    
    def _load(self):
        """从磁盘加载记忆"""
        # 加载 MEMORY
        if self.memory_path.exists():
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memory_entries = data.get("entries", [])
            except (json.JSONDecodeError, FileNotFoundError):
                self.memory_entries = []
        else:
            self.memory_entries = []
        
        # 加载 USER
        if self.user_path.exists():
            try:
                with open(self.user_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_entries = data.get("entries", [])
            except (json.JSONDecodeError, FileNotFoundError):
                self.user_entries = []
        else:
            self.user_entries = []
    
    def _save_memory(self):
        """保存 MEMORY 到磁盘"""
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            json.dump({
                "entries": self.memory_entries,
                "char_limit": self.memory_char_limit
            }, f, ensure_ascii=False, indent=2)
    
    def _save_user(self):
        """保存 USER 到磁盘"""
        with open(self.user_path, 'w', encoding='utf-8') as f:
            json.dump({
                "entries": self.user_entries,
                "char_limit": self.user_char_limit
            }, f, ensure_ascii=False, indent=2)
    
    def _char_count(self, entries: List[str]) -> int:
        """计算条目列表的总字符数"""
        return sum(len(entry) for entry in entries)
    
    def _render_memory_block(self) -> str:
        """
        渲染记忆块（用于注入System Prompt）
        模仿 Hermes 的视觉效果
        """
        if not self.memory_entries:
            return ""
        
        lines = ["═════════════════════════════════════════════"]
        lines.append("MEMORY (我的个人笔记)")
        
        usage_memory = self._char_count(self.memory_entries)
        percent = int(usage_memory / self.memory_char_limit * 100)
        lines.append(f"[{percent}% — {usage_memory:,}/{self.memory_char_limit:,} 字符]")
        lines.append("═════════════════════════════════════════════")
        
        for entry in self.memory_entries:
            lines.append(f"§ {entry}")
        
        return "\n".join(lines)
    
    def _render_user_block(self) -> str:
        """渲染用户画像块"""
        if not self.user_entries:
            return ""
        
        lines = ["═════════════════════════════════════════════"]
        lines.append("USER PROFILE (用户画像)")
        
        usage_user = self._char_count(self.user_entries)
        percent = int(usage_user / self.user_char_limit * 100)
        lines.append(f"[{percent}% — {usage_user:,}/{self.user_char_limit:,} 字符]")
        lines.append("═════════════════════════════════════════════")
        
        for entry in self.user_entries:
            lines.append(f"§ {entry}")
        
        return "\n".join(lines)
    
    def get_memory_context(self) -> str:
        """
        获取完整的记忆上下文（用于注入System Prompt）
        返回格式化的文本块
        """
        blocks = []
        memory_block = self._render_memory_block()
        user_block = self._render_user_block()
        
        if memory_block:
            blocks.append(memory_block)
        if user_block:
            blocks.append(user_block)
        
        return "\n\n".join(blocks)
    
    def add_memory(self, content: str) -> Dict:
        """向 MEMORY 添加条目"""
        new_total = self._char_count(self.memory_entries) + len(content)
        
        if new_total > self.memory_char_limit:
            return {
                "success": False,
                "error": f"MEMORY已达上限 {self.memory_char_limit:,} 字符，当前 {new_total - len(content):,} 字符。请先删除或合并旧条目。",
                "current_entries": self.memory_entries
            }
        
        self.memory_entries.append(content)
        self._save_memory()
        return {"success": True, "message": f"已添加到MEMORY", "new_entries": self.memory_entries}
    
    def add_user(self, content: str) -> Dict:
        """向 USER 添加条目"""
        new_total = self._char_count(self.user_entries) + len(content)
        
        if new_total > self.user_char_limit:
            return {
                "success": False,
                "error": f"USER已达上限 {self.user_char_limit:,} 字符，当前 {new_total - len(content):,} 字符。请先删除或合并旧条目。",
                "current_entries": self.user_entries
            }
        
        self.user_entries.append(content)
        self._save_user()
        return {"success": True, "message": f"已添加到USER", "new_entries": self.user_entries}
    
    def replace_memory(self, old_text: str, new_content: str) -> Dict:
        """替换 MEMORY 中包含指定文本的条目（Hermes使用子字符串匹配）"""
        target_index = -1
        for i, entry in enumerate(self.memory_entries):
            if old_text in entry:
                target_index = i
                break
        
        if target_index == -1:
            return {"success": False, "error": f"未找到包含 '{old_text}' 的条目"}
        
        self.memory_entries[target_index] = new_content
        self._save_memory()
        return {"success": True, "message": f"已替换MEMORY条目", "new_entry": new_content}
    
    def replace_user(self, old_text: str, new_content: str) -> Dict:
        """替换 USER 中包含指定文本的条目"""
        target_index = -1
        for i, entry in enumerate(self.user_entries):
            if old_text in entry:
                target_index = i
                break
        
        if target_index == -1:
            return {"success": False, "error": f"未找到包含 '{old_text}' 的条目"}
        
        self.user_entries[target_index] = new_content
        self._save_user()
        return {"success": True, "message": f"已替换USER条目", "new_entry": new_content}
    
    def remove_memory(self, old_text: str) -> Dict:
        """从 MEMORY 删除包含指定文本的条目"""
        new_entries = []
        removed = False
        for entry in self.memory_entries:
            if old_text in entry:
                removed = True
            else:
                new_entries.append(entry)
        
        if not removed:
            return {"success": False, "error": f"未找到包含 '{old_text}' 的条目"}
        
        self.memory_entries = new_entries
        self._save_memory()
        return {"success": True, "message": f"已删除MEMORY条目"}
    
    def remove_user(self, old_text: str) -> Dict:
        """从 USER 删除包含指定文本的条目"""
        new_entries = []
        removed = False
        for entry in self.user_entries:
            if old_text in entry:
                removed = True
            else:
                new_entries.append(entry)
        
        if not removed:
            return {"success": False, "error": f"未找到包含 '{old_text}' 的条目"}
        
        self.user_entries = new_entries
        self._save_user()
        return {"success": True, "message": f"已删除USER条目"}
    
    def list_entries(self) -> Dict:
        """列出所有条目"""
        return {
            "memory": {
                "entries": self.memory_entries,
                "usage": f"{self._char_count(self.memory_entries)}/{self.memory_char_limit} 字符"
            },
            "user": {
                "entries": self.user_entries,
                "usage": f"{self._char_count(self.user_entries)}/{self.user_char_limit} 字符"
            }
        }