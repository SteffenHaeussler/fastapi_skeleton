import time
import uuid

from fastapi import Request
from loguru import logger
from opentelemetry import trace

from src.app.context import ctx_request_id


def _trace_fields() -> dict[str, str]:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return {}
    return {
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
    }


class RequestTimer:
    async def __call__(self, request: Request, call_next):
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.bind(
                method=request.method,
                path=request.url.path,
                status=500,
                duration_ms=round(duration_ms, 3),
                request_id=ctx_request_id.get(),
                **_trace_fields(),
            ).exception("request")
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Process-Time"] = str(duration_ms / 1000.0)
        logger.bind(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 3),
            request_id=ctx_request_id.get(),
            **_trace_fields(),
        ).info("request")

        return response


async def add_request_id(request: Request, call_next):
    incoming = request.headers.get("x-request-id")
    request_id = incoming if incoming else uuid.uuid4().hex
    request.state.request_id = request_id
    token = ctx_request_id.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        ctx_request_id.reset(token)
