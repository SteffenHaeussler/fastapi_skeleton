import time
import logging
import uuid

from fastapi import Request

from app.context import ctx_request_id


logger = logging.getLogger()


class RequestTimer:
    async def __call__(self, request: Request, call_next):
        logger.info("Incoming request")
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        logger.info(f"Processing this request took {process_time} seconds")

        return response


class RequestIdGenerator:
    async def __call__(self, request: Request, call_next):
        request_id = str(uuid.uuid4())

        ctx_request_id.set(request_id)
        response = await call_next(request)
        response.headers["request_id"] = request_id
        return response
