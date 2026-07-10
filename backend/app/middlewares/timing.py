from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - started_at
        response.headers["X-Process-Time"] = f"{duration:.4f}"
        return response
