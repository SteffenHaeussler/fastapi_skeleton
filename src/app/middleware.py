import time
import uuid

from fastapi import Request
from loguru import logger

from src.app.context import ctx_request_id


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
        ).info("request")

        return response


async def add_request_id(request: Request, call_next):
    incoming = request.headers.get("x-request-id")
    request_id = incoming if incoming else uuid.uuid4().hex
    ctx_request_id.set(request_id)
    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    return response
