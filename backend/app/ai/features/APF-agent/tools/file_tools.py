# tools/file_tools.py
"""
文件操作工具集
包含：读取文件、写入文件、执行Shell命令
"""

import os
import subprocess
import json
from typing import Dict, Any
from .registry import tool_registry


# ============================================================
# 工具1: read_file - 读取文件
# ============================================================

def read_file_handler(path: str) -> Dict[str, Any]:
    """
    读取文件内容的执行函数（Handler）
    
    参数:
        path: 文件路径
    
    返回:
        包含success和content/error的字典
    """
    try:
        # 获取绝对路径（基于当前工作目录）
        abs_path = os.path.abspath(path)
        
        # 检查文件是否存在
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"文件不存在: {abs_path}"
            }
        
        # 读取文件内容
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content,
            "path": abs_path
        }
    
    except PermissionError:
        return {"success": False, "error": f"没有权限读取文件: {path}"}
    except UnicodeDecodeError:
        return {"success": False, "error": f"文件不是文本格式（编码错误）: {path}"}
    except Exception as e:
        return {"success": False, "error": f"读取文件失败: {str(e)}"}


# read_file 的 JSON Schema（给LLM看）
READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取指定路径的文件内容。可用于查看配置文件、日志文件、代码文件、文档等。支持相对路径和绝对路径。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要读取的文件路径，例如 'config.json' 或 '/home/user/data.txt'"
                }
            },
            "required": ["path"]
        }
    }
}


# ============================================================
# 工具2: write_file - 写入文件
# ============================================================

def write_file_handler(path: str, content: str) -> Dict[str, Any]:
    """
    写入文件内容的执行函数（Handler）
    
    参数:
        path: 文件路径
        content: 要写入的内容
    """
    try:
        abs_path = os.path.abspath(path)
        
        # 确保目录存在
        directory = os.path.dirname(abs_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # 写入文件
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"文件已成功写入: {abs_path}",
            "bytes_written": len(content.encode('utf-8'))
        }
    
    except PermissionError:
        return {"success": False, "error": f"没有权限写入文件: {path}"}
    except Exception as e:
        return {"success": False, "error": f"写入文件失败: {str(e)}"}


WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "将内容写入指定路径的文件。如果文件不存在会创建，如果存在会覆盖。写入前会自动创建所需的目录。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要写入的文件路径，例如 'output.txt' 或 'logs/result.json'"
                },
                "content": {
                    "type": "string",
                    "description": "要写入文件的内容"
                }
            },
            "required": ["path", "content"]
        }
    }
}


# ============================================================
# 工具3: execute_shell - 执行Shell命令
# ============================================================

def execute_shell_handler(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    执行Shell命令的执行函数（Handler）
    
    参数:
        command: 要执行的Shell命令
        timeout: 超时时间（秒）
    """
    try:
        # 执行命令，捕获stdout和stderr
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout if result.stdout else "",
            "stderr": result.stderr if result.stderr else "",
            "command": command
        }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"命令执行超时（{timeout}秒）: {command}"
        }
    except Exception as e:
        return {"success": False, "error": f"执行命令失败: {str(e)}"}


EXECUTE_SHELL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_shell",
        "description": "执行Shell命令并返回输出结果。可用于运行系统命令、执行脚本、查询系统信息等。注意：这是一个强大的工具，请谨慎使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的Shell命令，例如 'ls -la' 或 'python script.py'"
                },
                "timeout": {
                    "type": "integer",
                    "description": "命令执行的超时时间（秒），默认30秒",
                    "default": 30
                }
            },
            "required": ["command"]
        }
    }
}


# ============================================================
# 注册所有工具到注册中心
# ============================================================

def register_all_tools():
    """注册所有文件操作工具"""
    tool_registry.register("read_file", READ_FILE_SCHEMA, read_file_handler)
    tool_registry.register("write_file", WRITE_FILE_SCHEMA, write_file_handler)
    tool_registry.register("execute_shell", EXECUTE_SHELL_SCHEMA, execute_shell_handler)


# 模块导入时自动注册
register_all_tools()