from __future__ import annotations

import time
from typing import Callable
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

from sample.contracts.errors import ErrorEnvelope
from sample.adapters.observability.logging import get_logger
from sample.adapters.observability.metrics import (
    http_request_duration_seconds,
    http_requests_total,
)


logger = get_logger()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        span = trace.get_current_span()
        span_context = span.get_span_context() if span else None
        trace_id = (
            format(span_context.trace_id, "032x")
            if span_context and span_context.trace_id != 0
            else None
        )
        bind_contextvars(request_id=request_id, route=request.url.path, trace_id=trace_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # defensive JSON error envelope
            logger.exception(
                "unhandled_exception",
                path=request.url.path,
                request_id=request_id,
                exc_info=True,
            )
            envelope = ErrorEnvelope(
                type="internal",
                message="Internal server error",
                retryable=False,
                status_code=500,
            )
            response = JSONResponse(status_code=500, content=envelope.model_dump())

        latency = time.perf_counter() - start
        status = str(response.status_code)
        route = request.url.path

        http_requests_total.labels(route=route, method=request.method, status=status).inc()
        http_request_duration_seconds.labels(
            route=route, method=request.method, status=status
        ).observe(latency)

        response.headers["x-request-id"] = request_id
        clear_contextvars()
        return response
