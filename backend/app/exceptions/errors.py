from __future__ import annotations  # 启用 PEP 604 等新特性的类型注解支持（Python 3.7+ 兼容）

class AppError(Exception):
    """应用自定义异常基类，用于统一 API 错误响应结构。"""
    
    def __init__(self, message: str, *, status_code: int = 400, code: str = "app_error", details: dict | None = None):
        """
        初始化应用异常实例。

        Args:
            message: 人类可读的错误提示信息。
            status_code: HTTP 状态码，默认为 400（Bad Request）。
            code: 机器可读的错误代码，便于客户端程序化处理，默认为 "app_error"。
            details: 可选的附加错误详情字典，用于提供更细粒度的错误上下文。
        """
        super().__init__(message)          # 调用内置 Exception 的初始化，存储 message 作为异常信息
        self.message = message             # 显式保存消息，方便外部直接访问
        self.status_code = status_code     # HTTP 状态码
        self.code = code                   # 错误代码
        self.details = details or {}       # 确保 details 总是字典，避免 None 带来的空值判断

class NotFoundError(AppError):
    """资源未找到异常，对应 HTTP 404。"""
    
    def __init__(self, message: str = "Resource not found", *, details: dict | None = None):
        """
        初始化资源未找到异常。

        Args:
            message: 错误消息，默认 'Resource not found'。
            details: 可选的附加错误详情。
        """
        # 固定状态码为 404，错误码为 "not_found"，并传递消息与详情
        super().__init__(message, status_code=404, code="not_found", details=details)


class ConflictError(AppError):
    """资源冲突异常，对应 HTTP 409。"""
    
    def __init__(self, message: str = "Resource conflict", *, details: dict | None = None):
        """
        初始化资源冲突异常。

        Args:
            message: 错误消息，默认 'Resource conflict'。
            details: 可选的附加错误详情。
        """
        # 固定状态码为 409，错误码为 "conflict"，并传递消息与详情
        super().__init__(message, status_code=409, code="conflict", details=details)