# tools/registry.py（扩展版）

from typing import Dict, Any, Callable, Optional
import functools
import json

class ToolRegistry:
    """
    工具注册中心（单例模式）- 扩展版
    
    新增功能：
    - 装饰器注册 (@tool_registry.tool)
    - 批量获取Schemas
    - 工具存在性检查
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._schemas = []
        return cls._instance
    
    def register(self, name: str, schema: Dict[str, Any], handler: Callable):
        """注册工具（原有方法，保持不变）"""
        self._tools[name] = {
            "schema": schema,
            "handler": handler
        }
        # 移除同名旧 schema，防止重复
        self._schemas = [s for s in self._schemas
                     if s["function"]["name"] != name]
        self._schemas.append(schema)
        # 不在这里打印，避免重复输出
    
    def tool(self, name: str, description: str, **param_defs):
        """
        装饰器：简化工具定义
        
        使用方式:
            @registry.tool("calculate", "执行数学计算", 
                          expression="string:要计算的数学表达式")
            def calculate_handler(expression):
                return eval(expression)
        """
        def decorator(func):
            # 构建parameters JSON Schema
            properties = {}
            required = []
            
            for param_name, param_type_desc in param_defs.items():
                # 解析参数类型和描述，格式: "string:描述文字"
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
            
            self.register(name, schema, func)
            
            @functools.wraps(func)
            def wrapper(**kwargs):
                return func(**kwargs)
            
            return wrapper
        return decorator
    
    def get_schemas(self) -> list:
        """获取所有工具的Schema列表"""
        return self._schemas
    
    def get_handler(self, name: str) -> Optional[Callable]:
        """根据工具名称获取执行函数"""
        tool = self._tools.get(name)
        return tool["handler"] if tool else None
    
    def has_tool(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools
    
    def list_tools(self) -> list:
        """列出所有已注册的工具名称"""
        return list(self._tools.keys())
    
    def get_tool_info(self, name: str) -> Optional[Dict]:
        """获取工具信息"""
        return self._tools.get(name)

# 创建全局单例
tool_registry = ToolRegistry()

# 兼容旧代码的别名
registry = tool_registry