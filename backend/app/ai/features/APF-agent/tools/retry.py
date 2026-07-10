# tools/retry.py
"""
工具调用的重试机制
"""

import time
import functools
from typing import Any, Callable, Optional

def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器：工具调用失败时自动重试
    
    参数:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍数（指数退避）
        exceptions: 需要重试的异常类型
    
    使用示例:
        @retry_on_failure(max_retries=3, delay=0.5)
        def my_tool(...):
            # 可能失败的操作
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # 如果结果是字典且包含错误，也考虑重试
                    if isinstance(result, dict) and not result.get("success", True):
                        if attempt < max_retries:
                            print(f"   ⚠️ 重试 {attempt+1}/{max_retries}: {result.get('error', '未知错误')}")
                            time.sleep(current_delay)
                            current_delay *= backoff
                            continue
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"   ⚠️ 重试 {attempt+1}/{max_retries}: {str(e)}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        return {
                            "success": False,
                            "error": f"重试{max_retries}次后仍然失败: {str(e)}"
                        }
            
            return {
                "success": False,
                "error": f"所有重试均失败: {str(last_exception)}"
            }
        
        return wrapper
    return decorator