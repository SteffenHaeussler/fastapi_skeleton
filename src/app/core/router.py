from time import time

from fastapi import APIRouter, Request
from loguru import logger

from src.app.core.schema import HealthCheckResponse

core = APIRouter()


@core.get("/health", response_model=HealthCheckResponse)
def health(request: Request) -> HealthCheckResponse:
    logger.debug(f"Methode: {request.method} on {request.url.path}")
    return {"version": request.app.state.VERSION, "timestamp": time()}


@core.post("/health", response_model=HealthCheckResponse)
def health(request: Request) -> HealthCheckResponse:
    logger.debug(f"Methode: {request.method} on {request.url.path}")
    return {"version": request.app.state.VERSION, "timestamp": time()}
