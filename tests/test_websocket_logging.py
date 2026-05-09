from types import SimpleNamespace

import anyio
import pytest
from fastapi import WebSocketDisconnect

from src.app.core import router as core_router
from src.app.v1 import router as v1_router


class DisconnectingWebSocket:
    def __init__(self, path: str):
        self.accepted = False
        self.url = SimpleNamespace(path=path)
        self.app = SimpleNamespace(state=SimpleNamespace(VERSION="test"))

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        raise WebSocketDisconnect(code=1000)


class RecordingLogger:
    def __init__(self):
        self.bind_kwargs = None
        self.info_message = None

    def bind(self, **kwargs):
        self.bind_kwargs = kwargs
        return self

    def info(self, message):
        self.info_message = message


@pytest.mark.parametrize(
    ("router_module", "path"),
    [
        (core_router, "/ws/health"),
        (v1_router, "/v1/ws/health"),
    ],
)
def test_websocket_disconnect_logs_structured_fields(monkeypatch, router_module, path):
    websocket = DisconnectingWebSocket(path)
    logger = RecordingLogger()
    monkeypatch.setattr(router_module, "logger", logger)

    anyio.run(router_module.health_ws, websocket)

    assert websocket.accepted is True
    assert logger.bind_kwargs == {
        "event": "websocket.disconnect",
        "path": path,
        "close_code": 1000,
    }
    assert logger.info_message == "websocket disconnected"
