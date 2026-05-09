import io
import json
import sys
from contextlib import redirect_stdout

from fastapi.testclient import TestClient

from src.app.logging import setup_logger
from src.app.main import app


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
