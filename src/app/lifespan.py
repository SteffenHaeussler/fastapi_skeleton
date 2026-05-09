from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.resources = SimpleNamespace()
    app.state.readiness_checks = []
    app.state._closers = []
    logger.info("startup complete")
    try:
        yield
    finally:
        for closer in reversed(app.state._closers):
            try:
                await closer()
            except Exception:
                logger.exception("error during shutdown closer")
        logger.info("shutdown complete")
