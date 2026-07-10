# tools/__init__.py
"""
工具模块
自动发现并加载 tools/ 目录下的所有工具
"""

import os
import importlib
from pathlib import Path
from typing import List

from .registry import tool_registry

def discover_and_load_tools() -> List[str]:
    """
    自动发现并加载 tools/ 目录下的所有工具模块
    
    扫描流程：
    1. 获取当前目录（tools/）下的所有 .py 文件
    2. 跳过 __init__.py 和 registry.py
    3. 使用 importlib 动态导入每个模块
    4. 模块导入时会自动执行注册逻辑
    
    返回:
        已加载的工具名称列表
    """
    loaded_tools = []
    current_dir = Path(__file__).parent
    
    # 扫描所有 .py 文件
    for py_file in current_dir.glob("*.py"):
        # 跳过特殊文件
        if py_file.name in ["__init__.py", "registry.py"]:
            continue
        
        module_name = f"tools.{py_file.stem}"
        
        try:
            # 动态导入模块
            module = importlib.import_module(module_name)
            
            # 如果模块有自定义的初始化函数，调用它
            if hasattr(module, "register_all_tools"):
                module.register_all_tools()
            
            loaded_tools.extend(tool_registry.list_tools())
            print(f"   ✅ 已加载: {py_file.name}")
            
        except Exception as e:
            print(f"   ❌ 加载失败 {py_file.name}: {e}")
    
    return list(set(loaded_tools))  # 去重返回

def init_tools():
    """初始化工具系统（在Agent启动时调用）"""
    print("📦 正在加载工具库...")
    tools = discover_and_load_tools()
    print(f"📦 共加载 {len(tools)} 个工具")
    return tools

# 模块导入时自动初始化
_loaded = init_tools()