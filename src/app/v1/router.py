import asyncio
from time import time

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from loguru import logger

from src.app.v1.schema import HealthCheckResponse

v1 = APIRouter()


@v1.get("/health", response_model=HealthCheckResponse)
def health(request: Request) -> HealthCheckResponse:
    logger.debug(f"Methode: {request.method} on {request.url.path}")
    return {"version": request.app.state.VERSION, "timestamp": time()}


@v1.post("/health", response_model=HealthCheckResponse)
def health(request: Request) -> HealthCheckResponse:
    logger.debug(f"Methode: {request.method} on {request.url.path}")
    return {"version": request.app.state.VERSION, "timestamp": time()}


@v1.websocket("/ws/health")
async def health(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            response = HealthCheckResponse(
                version=websocket.app.state.VERSION, timestamp=time()
            )

            await websocket.send_json(response.dict())

            await asyncio.sleep(10)

    except WebSocketDisconnect:
        print("Client disconnected")
