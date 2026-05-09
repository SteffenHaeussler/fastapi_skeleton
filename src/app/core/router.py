import asyncio
import inspect
from time import time

from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import ValidationError

from src.app.core.schema import (
    HealthCheckResponse,
    LivenessResponse,
    ReadinessResponse,
)

core = APIRouter()


@core.get("/health", response_model=HealthCheckResponse)
def health_get(request: Request) -> HealthCheckResponse:
    return {"version": request.app.state.VERSION, "timestamp": time()}


@core.post("/health", response_model=HealthCheckResponse)
def health_post(request: Request) -> HealthCheckResponse:
    return {"version": request.app.state.VERSION, "timestamp": time()}


@core.get("/health/live", response_model=LivenessResponse)
def health_live() -> LivenessResponse:
    return LivenessResponse(status="ok")


@core.get("/health/ready")
async def health_ready(request: Request, response: Response) -> ReadinessResponse:
    checks = list(getattr(request.app.state, "readiness_checks", []))

    async def _run(fn):
        try:
            result = fn()
            if inspect.isawaitable(result):
                result = await result
            return bool(result)
        except Exception:
            logger.exception("readiness check raised")
            return False

    results = await asyncio.gather(*[_run(fn) for _, fn in checks])
    statuses = {
        name: ("ok" if ok else "fail") for (name, _), ok in zip(checks, results)
    }
    overall = "ok" if all(results) else "degraded"
    response.status_code = 200 if overall == "ok" else 503
    return ReadinessResponse(status=overall, checks=statuses)


@core.websocket("/ws/health")
async def health_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            try:
                response = HealthCheckResponse(
                    version=websocket.app.state.VERSION, timestamp=time()
                )

                await websocket.send_json(response.model_dump())
            except ValidationError as e:
                logger.error(f"Validation Error: {e}")
                await websocket.send_json({"error": "Validation Error"})

            await asyncio.sleep(10)

    except WebSocketDisconnect:
        print("Client disconnected")
