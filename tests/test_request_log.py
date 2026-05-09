import io
import json
import sys
from contextlib import redirect_stdout

from fastapi.testclient import TestClient

from src.app.logging import setup_logger
from src.app.context import ctx_request_id
from src.app.main import app
from src.app.middleware import add_request_id


def test_request_id_echoed_when_provided():
    with TestClient(app) as client:
        r = client.get("/health", headers={"X-Request-ID": "given-id"})
    assert r.status_code == 200
    assert r.headers["X-Request-ID"] == "given-id"


def test_request_id_generated_when_missing():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.headers["X-Request-ID"]
    assert len(r.headers["X-Request-ID"]) >= 16


def test_request_log_is_structured_with_required_fields():
    setup_logger("DEV", json_serialize=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        with TestClient(app) as client:
            client.get("/health", headers={"X-Request-ID": "log-id"})
        sys.stdout.flush()

    request_lines = []
    for line in buf.getvalue().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("message") == "request":
            request_lines.append(payload)

    assert request_lines, "no structured request log line was emitted"
    record = request_lines[-1]
    assert record["method"] == "GET"
    assert record["path"] == "/health"
    assert record["status"] == 200
    assert isinstance(record["duration_ms"], (int, float))
    assert record["duration_ms"] >= 0
    assert record["request_id"] == "log-id"


def test_x_process_time_header_still_present():
    with TestClient(app) as client:
        r = client.get("/health")
    assert "X-Process-Time" in r.headers


def test_request_id_context_is_restored_after_request():
    async def call_next(_request):
        from fastapi import Response

        assert ctx_request_id.get() == "scoped-id"
        return Response()

    async def run_request():
        from types import SimpleNamespace

        token = ctx_request_id.set("outer-id")
        try:
            request = type(
                "Request",
                (),
                {
                    "headers": {"x-request-id": "scoped-id"},
                    "state": SimpleNamespace(),
                },
            )()

            response = await add_request_id(request, call_next)

            assert response.headers["X-Request-ID"] == "scoped-id"
            assert ctx_request_id.get() == "outer-id"
        finally:
            ctx_request_id.reset(token)

    import anyio

    anyio.run(run_request)


def test_request_id_context_is_restored_when_downstream_raises():
    async def call_next(_request):
        assert ctx_request_id.get() == "failing-id"
        raise RuntimeError("boom")

    async def run_request():
        import pytest
        from types import SimpleNamespace

        token = ctx_request_id.set("outer-id")
        try:
            request = type(
                "Request",
                (),
                {
                    "headers": {"x-request-id": "failing-id"},
                    "state": SimpleNamespace(),
                },
            )()

            with pytest.raises(RuntimeError, match="boom"):
                await add_request_id(request, call_next)

            assert ctx_request_id.get() == "outer-id"
        finally:
            ctx_request_id.reset(token)

    import anyio

    anyio.run(run_request)
