# tools/search_tools.py
"""
会话搜索工具
让Agent能够主动从历史对话中检索相关信息
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from session_store import SessionStore
from .registry import tool_registry

# 创建全局会话存储实例
session_store = SessionStore()


# ============================================================
# 工具1: search_memory - 全文检索历史对话
# ============================================================

@tool_registry.tool(
    name="search_memory",
    description="在历史对话中全文搜索。当用户询问之前讨论过的问题、提到过某个概念或信息，需要从记忆中找回时使用。支持关键词搜索和短语匹配。",
    query="string:要搜索的关键词或短语，例如 '数据库配置' 或 '\"部署流程\"'",
    limit="integer:返回结果的最大数量，默认5条，可选"
)
def search_memory_handler(query: str, limit: int = 5) -> dict:
    """搜索历史对话"""
    print(f"   🔍 搜索历史记忆: {query}")
    
    results = session_store.search(query, limit=min(limit, 20))
    
    if not results:
        return {
            "success": True,
            "query": query,
            "result_count": 0,
            "message": f"没有找到包含 '{query}' 的历史对话"
        }
    
    # 格式化返回结果，便于LLM理解
    formatted_results = []
    for r in results:
        # 计算匹配片段预览
        user_preview = r["user_message"][:200] + "..." if len(r["user_message"]) > 200 else r["user_message"]
        assistant_preview = r["assistant_message"][:200] + "..." if len(r["assistant_message"]) > 200 else r["assistant_message"]
        
        formatted_results.append({
            "session_id": r["session_id"],
            "timestamp": r["timestamp"],
            "user_question": user_preview,
            "previous_answer": assistant_preview,
            "relevance_score": r.get("relevance_score", 0)
        })
    
    return {
        "success": True,
        "query": query,
        "result_count": len(results),
        "results": formatted_results,
        "full_results": results  # 包含完整文本，供深入查看
    }


# ============================================================
# 工具2: search_by_date - 按日期检索
# ============================================================

@tool_registry.tool(
    name="search_by_date",
    description="按日期范围搜索历史对话。当用户问及某个时间段之前讨论过的问题时使用。",
    start_date="string:起始日期，格式 YYYY-MM-DD，例如 '2026-04-01'",
    end_date="string:结束日期，格式 YYYY-MM-DD，例如 '2026-04-23'",
    limit="integer:返回结果的最大数量，默认10条，可选"
)
def search_by_date_handler(start_date: str, end_date: str, limit: int = 10) -> dict:
    """按时间范围搜索"""
    print(f"   📅 按日期搜索: {start_date} 至 {end_date}")
    
    results = session_store.search_by_time_range(start_date, end_date, limit)
    
    if not results:
        return {
            "success": True,
            "start_date": start_date,
            "end_date": end_date,
            "result_count": 0,
            "message": f"在 {start_date} 至 {end_date} 期间没有找到对话记录"
        }
    
    formatted_results = []
    for r in results:
        formatted_results.append({
            "timestamp": r["timestamp"],
            "user_question": r["user_message"][:200] + "..." if len(r["user_message"]) > 200 else r["user_message"],
            "previous_answer": r["assistant_message"][:200] + "..." if len(r["assistant_message"]) > 200 else r["assistant_message"]
        })
    
    return {
        "success": True,
        "start_date": start_date,
        "end_date": end_date,
        "result_count": len(results),
        "results": formatted_results
    }


# ============================================================
# 工具3: get_session_stats - 获取记忆统计
# ============================================================

@tool_registry.tool(
    name="get_session_stats",
    description="获取会话数据库的统计信息，包括总对话轮次数、总会话数等。",
    no_input="string:占位参数，忽略此值"
)
def get_session_stats_handler(no_input: str = "") -> dict:
    """获取记忆统计信息"""
    stats = session_store.get_stats()
    
    return {
        "success": True,
        "stats": stats,
        "message": f"数据库中共有 {stats['total_exchanges']} 轮对话，{stats['total_sessions']} 个会话"
    }


def register_all_tools():
    """注册所有搜索工具"""
    pass