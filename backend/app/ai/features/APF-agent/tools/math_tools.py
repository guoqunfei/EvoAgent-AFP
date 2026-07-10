# tools/math_tools.py
"""
数学计算工具集
包含：表达式计算、基础数学运算等
"""

import math
import ast
import operator
from typing import Any
from .registry import tool_registry


# 安全的数学运算映射
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_eval(expr: str) -> Any:
    """
    安全地计算数学表达式
    
    只允许数字、基本运算符和数学函数，不允许__import__等危险操作
    """
    # 允许的名称（安全的函数和常量）
    safe_names = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "pi": math.pi,
        "e": math.e,
        "ceil": math.ceil,
        "floor": math.floor,
    }
    
    # 使用eval但限制命名空间
    return eval(expr, {"__builtins__": {}}, safe_names)


# ============================================================
# 工具1: calculate - 数学表达式计算
# ============================================================

@tool_registry.tool(
    name="calculate",
    description="执行数学计算，支持加减乘除、乘方、三角函数、对数等。支持的自然语言表达式如 '2+2*3'、'sqrt(16)'、'sin(30)'、'log(100)'。",
    expression="string:要计算的数学表达式，例如 '2+2*3'、'sqrt(16)'、'sin(30)'、'log(100)'"
)
def calculate_handler(expression: str) -> dict:
    """
    执行数学计算
    
    参数:
        expression: 数学表达式（字符串）
    
    返回:
        计算结果
    """
    try:
        # 清理表达式
        expr = expression.strip().replace(" ", "")
        
        # 检查是否有危险字符
        dangerous = ['__', 'import', 'exec', 'eval', 'open', 'file', 'input']
        for d in dangerous:
            if d in expr:
                return {
                    "success": False,
                    "error": f"表达式包含不允许的关键词: {d}"
                }
        
        # 计算
        result = safe_eval(expr)
        
        return {
            "success": True,
            "expression": expression,
            "result": result,
            "result_type": type(result).__name__
        }
    
    except ZeroDivisionError:
        return {"success": False, "error": "除零错误"}
    except SyntaxError as e:
        return {"success": False, "error": f"表达式语法错误: {e}"}
    except NameError as e:
        return {"success": False, "error": f"表达式中使用了未定义的名称: {e}"}
    except Exception as e:
        return {"success": False, "error": f"计算失败: {e}"}


# ============================================================
# 工具2: basic_math - 基础数学运算
# ============================================================

@tool_registry.tool(
    name="basic_math",
    description="执行基础数学运算，包括加、减、乘、除、取模、乘方等。",
    a="number:第一个数字",
    b="number:第二个数字",
    operation="string:运算类型，可选: add(加法), subtract(减法), multiply(乘法), divide(除法), modulo(取模), power(乘方)"
)
def basic_math_handler(a: float, b: float, operation: str) -> dict:
    """
    基础数学运算
    
    参数:
        a: 第一个数字
        b: 第二个数字
        operation: 运算类型
    """
    ops = {
        "add": (operator.add, "加法"),
        "subtract": (operator.sub, "减法"),
        "multiply": (operator.mul, "乘法"),
        "divide": (operator.truediv, "除法"),
        "modulo": (operator.mod, "取模"),
        "power": (operator.pow, "乘方"),
    }
    
    op_func, op_name = ops.get(operation, (None, None))
    
    if op_func is None:
        return {
            "success": False,
            "error": f"未知运算: {operation}",
            "available_operations": list(ops.keys())
        }
    
    try:
        result = op_func(a, b)
        return {
            "success": True,
            "operation": op_name,
            "a": a,
            "b": b,
            "result": result
        }
    except ZeroDivisionError:
        return {"success": False, "error": "除零错误"}
    except Exception as e:
        return {"success": False, "error": f"计算失败: {e}"}


def register_all_tools():
    """注册所有数学工具"""
    pass