import asyncio
from time import time

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import ValidationError

from src.app.core.schema import HealthCheckResponse

core = APIRouter()


@core.get("/health", response_model=HealthCheckResponse)
def health_get(request: Request) -> HealthCheckResponse:
    return {"version": request.app.state.VERSION, "timestamp": time()}


@core.post("/health", response_model=HealthCheckResponse)
def health_post(request: Request) -> HealthCheckResponse:
    return {"version": request.app.state.VERSION, "timestamp": time()}


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
