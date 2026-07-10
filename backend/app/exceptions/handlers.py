from __future__ import annotations  # 启用前向引用类型注解的支持

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions.errors import AppError  # 导入自定义的 AppError 异常基类

def register_exception_handlers(app: FastAPI) -> None:
    """
    向 FastAPI 应用注册全局异常处理器。

    该函数为 `AppError` 及其子类注册专用处理器，并为所有未捕获的 `Exception`
    注册一个兜底处理器，统一将异常转换为结构化的 JSON 响应。
    """

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """
        处理所有继承自 AppError 的自定义异常。

        Args:
            request: 触发异常的请求对象。
            exc: 被捕获的 AppError 实例，包含 status_code、code、message 和 details 等信息。

        Returns:
            一个 JSONResponse，其 HTTP 状态码和内容由异常实例的属性决定。
        """
        return JSONResponse(
            status_code=exc.status_code,  # 使用异常中定义的状态码（如 400、404、409 等）
            content={
                "success": False,         # 统一标记为失败
                "error": {
                    "code": exc.code,     # 机器可读的错误代码（如 "not_found"）
                    "message": exc.message,  # 人类可读的错误消息
                    "details": exc.details,  # 附加的错误详情字典
                },
                "request_id": getattr(request.state, "request_id", None),  # 尝试从请求状态获取请求 ID，若不存在则为 None
            },
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """
        兜底处理器：捕获所有未被 AppError 捕获器处理的异常（如代码 bug 或未预料的错误）。

        Args:
            request: 触发异常的请求对象。
            exc: 被捕获的任意异常实例。

        Returns:
            一个 HTTP 500 的 JSONResponse，包含固定错误代码 "internal_error" 和异常消息。
        """
        return JSONResponse(
            status_code=500,                      # 未预期的错误统一返回 500
            content={
                "success": False,
                "error": {
                    "code": "internal_error",     # 固定的内部错误代码
                    "message": str(exc),          # 将异常转换为字符串作为消息（生产环境可隐藏细节）
                    "details": {},                # 不对外暴露额外详情
                },
                "request_id": getattr(request.state, "request_id", None),
            },
        )