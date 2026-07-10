# tools/web_tools.py
"""
网页搜索工具集
包含：网页搜索、网页内容抓取等
"""

import requests
import json
import time
from typing import Dict, Any, Optional
from urllib.parse import quote_plus
from .registry import tool_registry


# 搜索引擎配置
SEARCH_ENGINES = {
    "duckduckgo": {
        "url": "https://api.duckduckgo.com/",
        "params": {"format": "json", "no_html": 1, "skip_disambig": 1}
    },
    "bing": {
        "url": "https://api.bing.microsoft.com/v7.0/search",
        "api_key_env": "BING_API_KEY"
    },
    "google": {
        "url": "https://www.googleapis.com/customsearch/v1",
        "api_key_env": "GOOGLE_API_KEY",
        "cx_env": "GOOGLE_SEARCH_ENGINE_ID"
    }
}

# 默认使用 DuckDuckGo（无需API Key）
DEFAULT_SEARCH_ENGINE = "duckduckgo"


def search_duckduckgo(query: str, max_results: int = 5) -> list:
    """
    使用 DuckDuckGo API 搜索
    
    DuckDuckGo 是少数提供免费搜索API的搜索引擎，无需API Key。
    """
    try:
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        
        # 处理摘要信息
        if data.get("AbstractText"):
            results.append({
                "title": data.get("AbstractTitle", query),
                "snippet": data.get("AbstractText", ""),
                "url": data.get("AbstractURL", "")
            })
        
        # 处理相关主题
        for topic in data.get("RelatedTopics", [])[:max_results-1]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "").split("-")[0][:100],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", "")
                })
        
        return results[:max_results]
    
    except requests.RequestException as e:
        print(f"搜索出错: {e}")
        return []


# ============================================================
# 工具1: web_search - 网页搜索
# ============================================================

@tool_registry.tool(
    name="web_search",
    description="在互联网上搜索信息。当用户询问实时信息、新闻、最新事件或你不确定答案的内容时使用。支持DuckDuckGo搜索（免费）。",
    query="string:搜索关键词，如 '2026年人工智能发展'",
    max_results="integer:返回的最大结果数量，默认5条，可选"
)
def web_search_handler(query: str, max_results: int = 5) -> dict:
    """
    执行网页搜索
    
    参数:
        query: 搜索关键词
        max_results: 返回的最大结果数
    
    返回:
        搜索结果列表
    """
    print(f"   🌐 正在搜索: {query}")
    
    results = search_duckduckgo(query, min(max_results, 10))
    
    if not results:
        return {
            "success": False,
            "error": "搜索失败或无结果",
            "query": query
        }
    
    return {
        "success": True,
        "query": query,
        "result_count": len(results),
        "results": results
    }


# ============================================================
# 工具2: fetch_url - 获取网页内容
# ============================================================

@tool_registry.tool(
    name="fetch_url",
    description="获取指定URL的网页内容。用于读取网页、API响应等。注意：可能受反爬虫机制限制。",
    url="string:要获取的网页URL",
    timeout="integer:超时时间（秒），默认30秒，可选"
)
def fetch_url_handler(url: str, timeout: int = 30) -> dict:
    """
    获取网页内容
    
    参数:
        url: 网页URL
        timeout: 超时时间
    
    返回:
        网页内容
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # 限制返回内容长度
        content = response.text
        truncated = False
        if len(content) > 10000:
            content = content[:10000] + "\n... [内容已截断，超出10000字符]"
            truncated = True
        
        return {
            "success": True,
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", "unknown"),
            "content": content,
            "content_length": len(response.text),
            "truncated": truncated
        }
    
    except requests.Timeout:
        return {"success": False, "error": f"请求超时（{timeout}秒）"}
    except requests.HTTPError as e:
        return {"success": False, "error": f"HTTP错误: {e.response.status_code}"}
    except requests.RequestException as e:
        return {"success": False, "error": f"请求失败: {str(e)}"}


def register_all_tools():
    """注册所有网页工具"""
    pass