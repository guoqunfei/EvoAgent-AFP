"""
AFPAgent 工具注册中心 — 统一版

同时支持:
- 后端原有工具注册模式: registry.register(name, toolset, schema, handler, desc, emoji)
- APF-agent-02 工具注册模式: tool_registry.tool(name, desc, **params) 装饰器

提供:
- get_definitions() → OpenAI tool schemas
- get_schemas() → 兼容 APF-agent-02
- dispatch(name, args) → 分派工具调用（返回 JSON 字符串）
- get_handler(name) → 获取 handler 函数
"""

import ast
import importlib
import json
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional
import functools


def tool_result(data: dict) -> str:
    """将结果字典转换为JSON字符串"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def tool_error(message: str) -> str:
    """生成错误结果JSON"""
    return json.dumps({"success": False, "error": message}, ensure_ascii=False)


class ToolEntry:
    """工具条目的元数据"""
    __slots__ = ("name", "toolset", "schema", "handler", "description", "emoji")

    def __init__(self, name, toolset, schema, handler, description="", emoji=""):
        self.name = name
        self.toolset = toolset
        self.schema = schema
        self.handler = handler
        self.description = description
        self.emoji = emoji


class ToolRegistry:
    """线程安全的工具注册中心单例 — 统一版"""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}
        self._lock = threading.RLock()

    # ---- 后端原有注册接口 ----
    def register(self, name: str, toolset: str = "afp", schema: dict = None,
                 handler: Callable = None, description: str = "", emoji: str = ""):
        """注册一个工具（兼容后端原有模式）"""
        with self._lock:
            # 如果 schema 未提供，用 description 构建
            if schema is None:
                schema = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description or name,
                        "parameters": {"type": "object", "properties": {}, "required": []}
                    }
                }
            self._tools[name] = ToolEntry(
                name=name, toolset=toolset, schema=schema,
                handler=handler, description=description, emoji=emoji
            )

    # ---- APF-agent-02 装饰器注册接口 ----
    def tool(self, name: str, description: str, **param_defs):
        """
        装饰器：简化工具定义 (兼容 APF-agent-02 模式)

        使用方式:
            @registry.tool("calculate", "执行数学计算",
                          expression="string:要计算的数学表达式")
            def calculate_handler(expression):
                return eval(expression)
        """
        def decorator(func):
            properties = {}
            required = []

            for param_name, param_type_desc in param_defs.items():
                if ":" in param_type_desc:
                    param_type, param_desc = param_type_desc.split(":", 1)
                else:
                    param_type = "string"
                    param_desc = param_type_desc

                properties[param_name] = {
                    "type": param_type,
                    "description": param_desc
                }
                required.append(param_name)

            schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            }

            self.register(name, "afp", schema, func, description)

            @functools.wraps(func)
            def wrapper(**kwargs):
                return func(**kwargs)

            return wrapper
        return decorator

    # ---- 查询接口 ----
    def get_definitions(self) -> List[dict]:
        """获取所有工具的 OpenAI Function Calling schema 列表"""
        with self._lock:
            return [entry.schema for entry in self._tools.values()]

    def get_schemas(self) -> list:
        """获取所有工具的 Schema 列表 (兼容 APF-agent-02)"""
        return self.get_definitions()

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        with self._lock:
            return list(self._tools.keys())

    def get_handler(self, name: str) -> Optional[Callable]:
        """根据工具名称获取执行函数 (兼容 APF-agent-02)"""
        with self._lock:
            entry = self._tools.get(name)
        return entry.handler if entry else None

    def has_tool(self, name: str) -> bool:
        """检查工具是否存在"""
        with self._lock:
            return name in self._tools

    def list_tools(self) -> list:
        """列出所有已注册的工具名称 (兼容 APF-agent-02)"""
        return self.get_tool_names()

    def get_tool_info(self, name: str) -> Optional[Dict]:
        """获取工具信息"""
        with self._lock:
            return self._tools.get(name)

    def dispatch(self, name: str, args: dict) -> str:
        """分派工具调用 — 返回 JSON 字符串"""
        with self._lock:
            entry = self._tools.get(name)
        if not entry:
            return tool_error(f"工具未找到: {name}")
        try:
            # APF-agent-02 风格的 handler 接收 **kwargs
            # 后端原有风格的 handler 接收 args dict
            import inspect
            sig = inspect.signature(entry.handler)
            params = list(sig.parameters.keys())

            if len(params) == 1 and params[0] == 'args':
                result = entry.handler(args)
            else:
                # 尝试匹配参数
                filtered = {}
                for k, v in args.items():
                    if k in params:
                        filtered[k] = v
                # 如果过滤后没有参数，可能是接收 dict 的
                if not filtered and len(params) == 1:
                    result = entry.handler(args)
                else:
                    try:
                        result = entry.handler(**filtered)
                    except TypeError:
                        result = entry.handler(args)

            if isinstance(result, dict):
                return tool_result(result)
            elif isinstance(result, str):
                # 如果已经是 JSON 字符串，直接返回
                try:
                    json.loads(result)
                    return result
                except (json.JSONDecodeError, ValueError):
                    return tool_result({"result": result})
            return str(result)
        except Exception as e:
            return tool_error(f"工具执行错误: {str(e)}")

    def get_tool_descriptions(self) -> str:
        """获取所有工具的描述文本(供LLM系统提示词使用)"""
        lines = []
        with self._lock:
            for name, entry in self._tools.items():
                desc = entry.schema.get("function", {}).get("description", entry.description)
                lines.append(f"- {name}: {desc}")
        return "\n".join(lines)


# 全局单例
registry = ToolRegistry()

# APF-agent-02 兼容别名
tool_registry = registry


def discover_tools(tools_dir: Optional[Path] = None) -> List[str]:
    """AST自动发现工具模块并导入"""
    tools_path = Path(tools_dir) if tools_dir else Path(__file__).resolve().parent
    module_names = [
        f"tools.{path.stem}"
        for path in sorted(tools_path.glob("*.py"))
        if path.name not in {"__init__.py", "registry.py"}
    ]

    imported = []
    for mod_name in module_names:
        try:
            importlib.import_module(mod_name)
            imported.append(mod_name)
        except Exception:
            pass
    return imported
