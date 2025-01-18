import time
import uuid

from fastapi import Request
from loguru import logger

from src.app.context import ctx_request_id


class RequestTimer:
    async def __call__(self, request: Request, call_next):
        logger.info("Incoming request")
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        logger.info(f"Processing this request took {process_time} seconds")

        return response


async def add_request_id(request: Request, call_next):
    ctx_request_id.set(uuid.uuid4().hex)
    response = await call_next(request)

    response.headers["x-request-id"] = ctx_request_id.get()
    return response
