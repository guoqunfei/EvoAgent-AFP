# gateway/user_manager.py
import os
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

# 导入前9讲实现的模块
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_agent import AIAgent
from memory_store import MemoryStore
from session_store import SessionStore
from skill_store import SkillStore


class UserSession:
    """
    单个用户的会话（包含独立的Agent实例、记忆和技能）
    
    Hermes的多用户隔离设计：每个Profile都有独立的config.yaml、.env、SOUL.md、
    记忆、会话、技能、Cron任务和状态数据库。
    """
    
    def __init__(
        self,
        user_id: str,
        user_name: str = "",
        data_root: str = "./data/users"
    ):
        self.user_id = user_id
        self.user_name = user_name
        
        # 用户专属数据目录
        self.user_dir = Path(data_root) / user_id
        self.memories_dir = self.user_dir / "memories"
        self.sessions_db = self.user_dir / "sessions.db"
        self.skills_dir = self.user_dir / "skills"
        
        self._init_directories()
        
        # 创建隔离的存储实例
        self.memory_store = MemoryStore(
            memory_path=str(self.memories_dir / "MEMORY.json"),
            user_path=str(self.memories_dir / "USER.json"),
        )
        
        self.session_store = SessionStore(str(self.sessions_db))
        self.skill_store = SkillStore(str(self.skills_dir))
        
        # 创建用户专属的Agent实例
        self.agent = AIAgent(
            memory_store=self.memory_store,
            session_store=self.session_store,
            skill_store=self.skill_store
        )
        
        self.last_active = datetime.now()
    
    def _init_directories(self):
        """创建用户专属目录结构"""
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_active = datetime.now()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取用户会话统计"""
        memory_stats = self.memory_store.list_entries()
        skill_stats = self.skill_store.get_stats()
        session_stats = self.session_store.get_stats()
        
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "last_active": self.last_active.isoformat(),
            "memory": memory_stats,
            "skills": skill_stats,
            "sessions": session_stats
        }


class UserManager:
    """
    多用户会话管理器
    
    负责：
    - 为每个用户创建隔离的Agent实例
    - 管理用户会话生命周期
    - 处理并发请求
    """
    
    def __init__(self, data_root: str = "./data/users"):
        self.data_root = Path(data_root)
        self.data_root.mkdir(parents=True, exist_ok=True)
        
        # user_id -> UserSession 映射
        self._sessions: Dict[str, UserSession] = {}
        
        # 加载已存在的用户
        self._load_existing_users()
    
    def _load_existing_users(self):
        """加载已存在的用户目录"""
        if not self.data_root.exists():
            return
        
        for user_dir in self.data_root.iterdir():
            if user_dir.is_dir():
                user_id = user_dir.name
                # 加载用户信息（如果存在）
                user_info_file = user_dir / "user_info.json"
                user_name = ""
                if user_info_file.exists():
                    with open(user_info_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                        user_name = info.get("name", "")
                
                self._sessions[user_id] = UserSession(
                    user_id=user_id,
                    user_name=user_name,
                    data_root=str(self.data_root)
                )
                print(f"📁 加载用户会话: {user_id} ({user_name})")
    
    def get_or_create_session(
        self,
        user_id: str,
        user_name: str = ""
    ) -> UserSession:
        """
        获取或创建用户会话
        
        Hermes的多用户支持核心：每个用户拥有完全独立的会话隔离，
        包括独立的记忆、技能和对话历史。
        """
        if user_id in self._sessions:
            session = self._sessions[user_id]
            session.update_activity()
            
            # 更新用户名（如果不同）
            if user_name and session.user_name != user_name:
                session.user_name = user_name
                self._save_user_info(user_id, user_name)
            
            return session
        
        # 创建新会话
        session = UserSession(
            user_id=user_id,
            user_name=user_name,
            data_root=str(self.data_root)
        )
        
        self._sessions[user_id] = session
        self._save_user_info(user_id, user_name)
        
        print(f"✨ 为新用户创建会话: {user_id} ({user_name})")
        
        return session
    
    def _save_user_info(self, user_id: str, user_name: str):
        """保存用户信息"""
        user_dir = self.data_root / user_id
        user_info_file = user_dir / "user_info.json"
        
        with open(user_info_file, 'w', encoding='utf-8') as f:
            json.dump({
                "name": user_name,
                "created_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    
    def get_session(self, user_id: str) -> Optional[UserSession]:
        """获取用户会话"""
        return self._sessions.get(user_id)
    
    def get_all_sessions(self) -> Dict[str, UserSession]:
        """获取所有活跃会话"""
        return self._sessions.copy()
    
    def cleanup_inactive_sessions(self, max_idle_minutes: int = 60):
        """
        清理不活跃的会话（释放内存）
        
        Hermes后台持久化设计：会话可以长期空闲，因为状态已经持久化，
        用户再次发消息时会重新加载。
        """
        from datetime import timedelta
        
        now = datetime.now()
        to_remove = []
        
        for user_id, session in self._sessions.items():
            if (now - session.last_active) > timedelta(minutes=max_idle_minutes):
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del self._sessions[user_id]
            print(f"🧹 清理不活跃会话: {user_id}")
        
        return len(to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        active_sessions = len(self._sessions)
        return {
            "active_sessions": active_sessions,
            "user_ids": list(self._sessions.keys())
        }


# 全局用户管理器实例
user_manager = UserManager()