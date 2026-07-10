# session_store.py
"""
会话历史存储模块
使用SQLite + FTS5存储和检索历史对话
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class SessionStore:
    """
    会话历史存储（SQLite + FTS5全文检索）
    
    Hermes设计思路：
    - 每次完整对话（user + assistant）作为一个Exchange
    - FTS5建立retrieval索引，支持全文搜索
    - Agent按需主动检索，而不是被动加载全部历史
    """
    
    def __init__(self, db_path: str = "./data/sessions.db"):
        """
        初始化会话存储
        
        参数:
            db_path: SQLite数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库：建立两张表——exchanges和fts虚拟表"""
        with sqlite3.connect(self.db_path) as conn:
            # 1. 创建主表：存储对话轮次的结构化数据
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exchanges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,           -- 会话ID，用于区分不同会话
                    timestamp TEXT NOT NULL,            -- ISO格式时间戳
                    user_message TEXT NOT NULL,         -- 用户消息
                    assistant_message TEXT NOT NULL,    -- Agent回复
                    tool_calls TEXT,                    -- JSON格式的工具调用记录
                    turn_number INTEGER,                -- 会话内轮次编号
                    summary TEXT                        -- LLM生成的摘要（可选）
                )
            """)
            
            # 2. 创建FTS5虚拟表：用于全文检索
            # 注意：FTS5虚拟表只需要索引需要搜索的字段
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS exchanges_fts 
                USING fts5(user_message, assistant_message, summary, content=exchanges, content_rowid=id)
            """)
            
            # 3. 创建触发器：自动同步主表和FTS表
            # INSERT触发器
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS exchanges_ai AFTER INSERT ON exchanges BEGIN
                    INSERT INTO exchanges_fts(rowid, user_message, assistant_message, summary)
                    VALUES (new.id, new.user_message, new.assistant_message, new.summary);
                END
            """)
            
            # UPDATE触发器
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS exchanges_au AFTER UPDATE ON exchanges BEGIN
                    UPDATE exchanges_fts 
                    SET user_message = new.user_message, 
                        assistant_message = new.assistant_message,
                        summary = new.summary
                    WHERE rowid = old.id;
                END
            """)
            
            # DELETE触发器
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS exchanges_ad AFTER DELETE ON exchanges BEGIN
                    DELETE FROM exchanges_fts WHERE rowid = old.id;
                END
            """)
            
            # 创建索引以加速按session_id和timestamp的查询
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON exchanges(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON exchanges(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_turn_number ON exchanges(turn_number)")
    
    def add_exchange(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        turn_number: int,
        tool_calls: Optional[List[Dict]] = None,
        summary: Optional[str] = None
    ) -> int:
        """
        添加一轮对话到数据库
        
        参数:
            session_id: 会话唯一标识
            user_message: 用户提问
            assistant_message: Agent回复
            turn_number: 会话内的轮次编号
            tool_calls: 工具调用记录（可选）
            summary: LLM生成的摘要（可选）
        
        返回:
            新记录的rowid
        """
        timestamp = datetime.now().isoformat()
        tool_calls_json = json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO exchanges (session_id, timestamp, user_message, assistant_message, 
                                     tool_calls, turn_number, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, timestamp, user_message, assistant_message, 
                 tool_calls_json, turn_number, summary)
            )
            return cursor.lastrowid
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        使用FTS5全文检索搜索历史对话
        
        参数:
            query: 搜索关键词（支持FTS5查询语法）
            limit: 最大返回结果数
        
        返回:
            匹配的exchange列表，按相关性排序
        
        示例query:
            - "Python" → 包含Python的单次
            - "部署 AND 配置" → 同时包含部署和配置
            - "\"文件系统\"" → 精确短语匹配
            - "文件*" → 前缀匹配
        """
        with sqlite3.connect(self.db_path) as conn:
            # 使用BM25算法进行相关性排序，BM25分数越低表示相关性越高
            cursor = conn.execute(
                """
                SELECT 
                    e.id, e.session_id, e.timestamp, e.user_message, e.assistant_message,
                    e.turn_number, e.summary,
                    bm25(exchanges_fts) as relevance_score
                FROM exchanges e
                JOIN exchanges_fts fts ON e.id = fts.rowid
                WHERE exchanges_fts MATCH ?
                ORDER BY bm25(exchanges_fts)
                LIMIT ?
                """,
                (query, limit)
            )
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "session_id": row[1],
                    "timestamp": row[2],
                    "user_message": row[3],
                    "assistant_message": row[4],
                    "turn_number": row[5],
                    "summary": row[6],
                    "relevance_score": row[7]
                })
            
            return results
    
    def search_by_time_range(
        self, 
        start_date: str, 
        end_date: str, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        按时间范围检索历史对话
        
        参数:
            start_date: 起始日期（ISO格式，如"2026-04-01"）
            end_date: 结束日期（ISO格式，如"2026-04-23"）
            limit: 最大返回结果数
        """
        with sqlite3.connect(self.db_path) as conn:
            # FIXED: Use date(timestamp) to compare dates correctly
            cursor = conn.execute(
                """
                SELECT 
                    id, session_id, timestamp, user_message, assistant_message, 
                    turn_number, summary
                FROM exchanges
                WHERE date(timestamp) >= date(?) AND date(timestamp) <= date(?)
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (start_date, end_date, limit)
            )
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "session_id": row[1],
                    "timestamp": row[2],
                    "user_message": row[3],
                    "assistant_message": row[4],
                    "turn_number": row[5],
                    "summary": row[6]
                })
            
            return results
    
    def search_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """获取指定会话的完整历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, timestamp, user_message, assistant_message, turn_number, summary
                FROM exchanges
                WHERE session_id = ?
                ORDER BY turn_number ASC
                """,
                (session_id,)
            )
            
            results = [] 
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "user_message": row[2],
                    "assistant_message": row[3],
                    "turn_number": row[4],
                    "summary": row[5]
                })
            
            return results
    
    def delete_exchange(self, exchange_id: int) -> bool:
        """删除指定对话记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM exchanges WHERE id = ?", (exchange_id,))
            return cursor.rowcount > 0
    
    def get_total_count(self) -> int:
        """获取数据库中的总记录数"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM exchanges")
            return cursor.fetchone()[0]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM exchanges")
            total = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(DISTINCT session_id) FROM exchanges")
            total_sessions = cursor.fetchone()[0]
            
            return {
                "total_exchanges": total,
                "total_sessions": total_sessions
            }
    
    def clear_old_records(self, days: int = 365) -> int:
        """清理超过指定天数的旧记录（容量管理策略）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM exchanges WHERE datetime(timestamp) < datetime('now', ?)",
                (f'-{days} days',)
            )
            return cursor.rowcount
        
    def consolidate_old_records(self, compress_threshold: int = 500) -> int:
        """
        容量整理策略：当记录超过阈值时，触发LLM-led压缩

        Hermes的设计：不是静默丢弃，而是让模型主动整理和压缩

        参数:
            compress_threshold: 触发压缩的记录数阈值

        返回:
            压缩后的新记录数
        """
        total = self.get_total_count()

        if total < compress_threshold:
            return total

        # 获取最旧的记录（超过阈值的部分）
        oldest_to_compress = total - compress_threshold

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, user_message, assistant_message, summary
                FROM exchanges
                ORDER BY id ASC
                LIMIT ?
                """,
                (oldest_to_compress,)
            )
            old_records = cursor.fetchall()

            if old_records:
                # 这里应该调用LLM进行摘要压缩
                # 实际实现中，将old_records发送给LLM生成摘要
                # 然后删除旧的记录，插入摘要作为新记录

                # 删除被压缩的旧记录
                ids_to_delete = [r[0] for r in old_records]
                placeholders = ','.join(['?'] * len(ids_to_delete))
                conn.execute(f"DELETE FROM exchanges WHERE id IN ({placeholders})", ids_to_delete)

        return self.get_total_count()

    def smart_prune(self, pruning_prompt: str) -> Dict[str, Any]:
        """
        智能修剪：让模型自己判断哪些记忆过时、应该删除或合并

        这是Hermes容量设计哲学的核心——把清理的权力交给模型
        """
        # 获取所有记忆（按时间排序）
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, timestamp, user_message, assistant_message
                FROM exchanges
                ORDER BY timestamp DESC
                LIMIT 200
                """
            )
            recent_exchanges = cursor.fetchall()

        if not recent_exchanges:
            return {"success": False, "message": "没有可修剪的记忆"}

        # 构建修剪建议请求
        current_entries = []
        for ex in recent_exchanges[:50]:
            current_entries.append({
                "id": ex[0],
                "timestamp": ex[1],
                "user": ex[2][:100],
                "assistant": ex[3][:100]
            })

        # 返回待修剪条目，让外部LLM判断（由Agent主循环处理修剪决策）
        return {
            "success": True,
            "needs_llm_decision": True,
            "current_entries": current_entries,
            "pruning_prompt": pruning_prompt,
            "total_entries": len(current_entries)
        }