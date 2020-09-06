import time

from fastapi import Request
from loguru import logger


class RequestTimer:
    async def __call__(self, request: Request, call_next):
        logger.info("Incoming request")
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        logger.info(f"Processing this request took {process_time} seconds")

        return response
