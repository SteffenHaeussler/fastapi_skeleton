# Production Microservice Basics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add production microservice scaffolding to the FastAPI skeleton: split `/health/live` and `/health/ready`, central exception handlers with stable error envelope, structured request/response logging, off-by-default CORS, FastAPI lifespan, and a small dependency pattern for shared resources.

**Architecture:** New app-level files (`errors.py`, `lifespan.py`, `dependencies.py`) hold cross-cutting concerns; `main.py` wires them in. Two existing middlewares are kept (separation of concerns) but the timer's log line becomes structured. Per-router error helpers (`core/errors.py`, `v1/errors.py`) get deleted in favor of `src/app/errors.py`. CORS is gated by per-deployment config and disabled by default.

**Tech Stack:** FastAPI, pydantic, pydantic-settings (TOML), loguru, pytest, httpx (test client only).

**Spec:** `docs/superpowers/specs/2026-05-09-production-microservice-basics-design.md`

---

## File Structure

| Path                                | Action  | Responsibility                                                       |
| ----------------------------------- | ------- | -------------------------------------------------------------------- |
| `src/app/errors.py`                 | New     | `ErrorResponse`, `APIException`, exception handlers, registrar.      |
| `src/app/lifespan.py`               | New     | `@asynccontextmanager` lifespan; sets up `app.state` slots.          |
| `src/app/dependencies.py`           | New     | `get_resources` factory + documented Annotated alias pattern.        |
| `src/app/middleware.py`             | Modify  | Header-aware request_id; structured request log.                     |
| `src/app/logging.py`                | Modify  | `sink_serializer` merges `record["extra"]` into JSON output.         |
| `src/app/config.py`                 | Modify  | Add `CORSConfig`; attach to `Deployment`.                            |
| `config.toml`                       | Modify  | Document per-deployment `[X.cors]` section (defaults work without).  |
| `src/app/main.py`                   | Modify  | Pass `lifespan`; register handlers; conditionally add CORS.          |
| `src/app/core/router.py`            | Modify  | Add `/health/live`, `/health/ready`. Drop `logger.debug` line.       |
| `src/app/core/schema.py`            | Modify  | Add `LivenessResponse`, `ReadinessResponse`.                         |
| `src/app/core/errors.py`            | Delete  | Duplicate helpers, unused.                                           |
| `src/app/v1/router.py`              | Modify  | Drop `logger.debug` line.                                            |
| `src/app/v1/errors.py`              | Delete  | Duplicate helpers + dead `APIException`, unused.                     |
| `tests/test_main.py`                | Modify  | Keep current health tests untouched.                                 |
| `tests/test_health.py`              | New     | `/health/live` + `/health/ready` tests.                              |
| `tests/test_errors.py`              | New     | Exception handler envelope tests.                                    |
| `tests/test_request_log.py`         | New     | Request-id header + structured log tests.                            |
| `tests/test_cors.py`                | New     | CORS off-by-default + on-when-enabled tests.                         |

Tasks are decomposed so each one ends in a green test run and a commit. The order reflects dependencies (config types → lifespan → handlers → middleware/logging → endpoints → CORS → cleanup).

---

## Conventions for the Engineer

- All paths are relative to repo root `/Users/steffen/conductor/workspaces/fastapi_skeleton/marseille`.
- Run tests with `uv run pytest <path> -v`. Run the whole suite at the end of each task.
- The project already imports as `src.app.*` (see `pyproject.toml: pythonpath = ["."]`). Keep that.
- Loguru `logger` is imported as `from loguru import logger`.
- The `ctx_request_id` context var lives in `src/app/context.py`.
- Commits use Conventional Commits style ("feat:", "refactor:", "test:", "chore:"), matching recent history.

---

## Task 1: Add `CORSConfig` to settings

**Files:**
- Modify: `src/app/config.py`
- Modify: `config.toml`

- [ ] **Step 1: Read the current config**

Skim `src/app/config.py` and `config.toml`. Note that `Deployment` currently has only `CONFIG_NAME` and `DEBUG`. Optional config blocks are read by pydantic-settings if present, defaulted otherwise.

- [ ] **Step 2: Write a failing test**

Create `tests/test_config.py`:

```python
from src.app.config import CORSConfig, Config


def test_cors_config_defaults_disabled():
    cors = CORSConfig()
    assert cors.enabled is False
    assert cors.allow_origins == []
    assert cors.allow_methods == ["GET", "POST"]
    assert cors.allow_headers == ["*"]
    assert cors.allow_credentials is False


def test_deployment_has_default_cors_config():
    config = Config()
    assert config.DEV.cors.enabled is False
    assert config.PROD.cors.enabled is False
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: ImportError for `CORSConfig` (does not exist yet).

- [ ] **Step 4: Add `CORSConfig` and attach it to `Deployment`**

Edit `src/app/config.py`. Add `CORSConfig` above `Deployment`, then add a default `cors` field on `Deployment`:

```python
class CORSConfig(BaseModel):
    enabled: bool = False
    allow_origins: list[str] = []
    allow_methods: list[str] = ["GET", "POST"]
    allow_headers: list[str] = ["*"]
    allow_credentials: bool = False


class Deployment(BaseModel):
    CONFIG_NAME: constr(to_upper=True)
    DEBUG: bool
    cors: CORSConfig = CORSConfig()
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_config.py -v`
Expected: both tests PASS.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add src/app/config.py tests/test_config.py
git commit -m "feat(config): add CORSConfig with defaults attached to Deployment"
```

---

## Task 2: Add lifespan with state slots

**Files:**
- Create: `src/app/lifespan.py`
- Modify: `src/app/main.py`

- [ ] **Step 1: Write a failing test**

Create `tests/test_lifespan.py`:

```python
from fastapi.testclient import TestClient

from src.app.main import app


def test_lifespan_initializes_state_slots():
    with TestClient(app) as client:
        client.get("/health")  # any request to trigger lifespan
        assert hasattr(app.state, "resources")
        assert hasattr(app.state, "readiness_checks")
        assert hasattr(app.state, "_closers")
        assert app.state.readiness_checks == []
        assert app.state._closers == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_lifespan.py -v`
Expected: FAIL — `app.state` lacks the new attributes.

- [ ] **Step 3: Create `src/app/lifespan.py`**

```python
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
```

- [ ] **Step 4: Wire the lifespan into `get_application`**

In `src/app/main.py`, change `application = FastAPI(openapi_tags=tags_metadata)` to:

```python
from src.app.lifespan import lifespan

# inside get_application:
application = FastAPI(lifespan=lifespan, openapi_tags=tags_metadata)
```

Add the import near the other `from src.app...` imports.

Also update the existing `application.state = config` line: `FastAPI(lifespan=...)` calls `lifespan(app)` and the lifespan sets attributes on `app.state`. Wholesale-assigning `application.state = config` clobbers those attributes. Replace with per-attribute assignment:

```python
for key, value in dict(config).items():
    setattr(application.state, key, value)
```

- [ ] **Step 5: Run the lifespan test**

Run: `uv run pytest tests/test_lifespan.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: every existing test still passes — including `tests/test_main.py` which checks `app.state.VERSION`.

If `test_main.py` fails because `app.state.VERSION` is gone, the per-attribute loop in Step 4 was not applied. Re-check.

- [ ] **Step 7: Commit**

```bash
git add src/app/lifespan.py src/app/main.py tests/test_lifespan.py
git commit -m "feat(lifespan): introduce FastAPI lifespan with resource/readiness/closer slots"
```

---

## Task 3: Add `ErrorResponse` schema and `APIException`

**Files:**
- Create: `src/app/errors.py` (schema + APIException only — handlers come next task)
- Test: `tests/test_errors.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_errors.py`:

```python
import pytest

from src.app.errors import APIException, ErrorResponse


def test_error_response_schema_fields():
    e = ErrorResponse(
        error="bad_request",
        message="bad input",
        status=400,
        request_id="abc",
    )
    dumped = e.model_dump()
    assert dumped == {
        "error": "bad_request",
        "message": "bad input",
        "status": 400,
        "request_id": "abc",
        "details": None,
    }


def test_api_exception_defaults():
    exc = APIException("boom")
    assert exc.status_code == 500
    assert exc.error_code == "internal_server_error"
    assert exc.message == "boom"
    assert exc.details is None


def test_api_exception_subclass_overrides():
    class NotFound(APIException):
        status_code = 404
        error_code = "not_found"

    exc = NotFound("missing", details={"id": 5})
    assert exc.status_code == 404
    assert exc.error_code == "not_found"
    assert exc.details == {"id": 5}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_errors.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create `src/app/errors.py`**

```python
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    message: str
    status: int
    request_id: str
    details: dict | None = None


class APIException(Exception):
    status_code: int = 500
    error_code: str = "internal_server_error"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_errors.py -v`
Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/app/errors.py tests/test_errors.py
git commit -m "feat(errors): add ErrorResponse schema and APIException base class"
```

---

## Task 4: Implement and register exception handlers

**Files:**
- Modify: `src/app/errors.py`
- Modify: `src/app/main.py`
- Modify: `tests/test_errors.py`

- [ ] **Step 1: Add handler integration tests**

Append to `tests/test_errors.py`:

```python
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel


def _make_app():
    """Build a minimal app with our error setup wired in.

    Avoid importing src.app.main here — we want a clean app surface to
    register one-off test routes, free of the production routers.
    """
    from src.app.errors import APIException, register_exception_handlers
    from src.app.middleware import add_request_id

    app = FastAPI()
    app.middleware("http")(add_request_id)
    register_exception_handlers(app)

    class Body(BaseModel):
        x: int

    @app.get("/raise-http")
    def _raise_http():
        raise HTTPException(status_code=400, detail="bad input")

    @app.get("/raise-http-dict")
    def _raise_http_dict():
        raise HTTPException(status_code=403, detail={"reason": "nope"})

    @app.get("/raise-api")
    def _raise_api():
        class NotFound(APIException):
            status_code = 404
            error_code = "not_found"
        raise NotFound("missing", details={"id": 5})

    @app.get("/raise-bare")
    def _raise_bare():
        raise RuntimeError("internal secret leak attempt")

    @app.post("/validate")
    def _validate(body: Body):
        return body

    return app


def test_http_exception_returns_envelope():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/raise-http")
    assert r.status_code == 400
    body = r.json()
    assert body["error"] == "bad_request"
    assert body["message"] == "bad input"
    assert body["status"] == 400
    assert body["request_id"]
    assert body["details"] is None


def test_http_exception_with_dict_detail_uses_details():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/raise-http-dict")
    assert r.status_code == 403
    body = r.json()
    assert body["error"] == "forbidden"
    assert body["details"] == {"reason": "nope"}


def test_api_exception_uses_subclass_status_and_code():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/raise-api")
    assert r.status_code == 404
    body = r.json()
    assert body["error"] == "not_found"
    assert body["message"] == "missing"
    assert body["details"] == {"id": 5}


def test_validation_error_envelope():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.post("/validate", json={"x": "not-an-int"})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validation_error"
    assert body["status"] == 422
    assert "errors" in body["details"]


def test_bare_exception_does_not_leak_message():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/raise-bare")
    assert r.status_code == 500
    body = r.json()
    assert body["error"] == "internal_server_error"
    assert body["message"] == "Internal server error"
    assert "secret leak" not in body["message"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_errors.py -v`
Expected: FAIL — `register_exception_handlers` does not exist.

- [ ] **Step 3: Implement handlers in `src/app/errors.py`**

Append to `src/app/errors.py`:

```python
from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from src.app.context import ctx_request_id


def _phrase_to_code(status: int) -> str:
    try:
        phrase = HTTPStatus(status).phrase
    except ValueError:
        return "http_error"
    return phrase.lower().replace(" ", "_").replace("-", "_")


def _envelope(*, error: str, message: str, status: int, details: dict | None = None) -> JSONResponse:
    payload = ErrorResponse(
        error=error,
        message=message,
        status=status,
        request_id=ctx_request_id.get(),
        details=details,
    )
    return JSONResponse(status_code=status, content=payload.model_dump())


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    status = exc.status_code
    if isinstance(exc.detail, dict):
        message = HTTPStatus(status).phrase if status in HTTPStatus._value2member_map_ else "HTTP error"
        details = exc.detail
    elif isinstance(exc.detail, str):
        message = exc.detail
        details = None
    else:
        message = HTTPStatus(status).phrase if status in HTTPStatus._value2member_map_ else "HTTP error"
        details = None
    return _envelope(error=_phrase_to_code(status), message=message, status=status, details=details)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _envelope(
        error="validation_error",
        message="Request validation failed",
        status=422,
        details={"errors": exc.errors()},
    )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    return _envelope(
        error=exc.error_code,
        message=exc.message,
        status=exc.status_code,
        details=exc.details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception")
    return _envelope(
        error="internal_server_error",
        message="Internal server error",
        status=500,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
```

- [ ] **Step 4: Wire `register_exception_handlers` into `get_application`**

In `src/app/main.py`, after the middleware registrations and before the router includes:

```python
from src.app.errors import register_exception_handlers

# inside get_application, after middleware setup:
register_exception_handlers(application)
```

- [ ] **Step 5: Run the error tests**

Run: `uv run pytest tests/test_errors.py -v`
Expected: all tests PASS.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: every test still passes.

- [ ] **Step 7: Commit**

```bash
git add src/app/errors.py src/app/main.py tests/test_errors.py
git commit -m "feat(errors): central exception handlers with stable error envelope"
```

---

## Task 5: Make logging serializer surface structured `extra`

**Files:**
- Modify: `src/app/logging.py`
- Test: indirectly via Task 6 (request log test)

This is a small prerequisite for Task 6: when `RequestTimer` calls `logger.bind(method=..., path=..., status=..., duration_ms=..., request_id=...).info("request")`, the JSON sink must include those fields. Today `sink_serializer` drops everything except level/message/timestamp/request_id.

- [ ] **Step 1: Write a focused test**

Create `tests/test_logging_sink.py`:

```python
import io
import json
import sys
from contextlib import redirect_stdout

from loguru import logger

from src.app.logging import setup_logger


def test_sink_serializer_includes_extra_fields():
    setup_logger("DEV", json_serialize=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        logger.bind(method="GET", path="/x", status=200, duration_ms=1.2).info("request")
        sys.stdout.flush()
    line = buf.getvalue().strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["message"] == "request"
    assert payload["method"] == "GET"
    assert payload["path"] == "/x"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 1.2
    assert "request_id" in payload
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_logging_sink.py -v`
Expected: FAIL — extras not present in JSON output.

- [ ] **Step 3: Update `sink_serializer`**

Edit `src/app/logging.py`, replace the body of `sink_serializer`:

```python
def sink_serializer(message):
    record = message.record
    simplified = {
        "level": record["level"].name,
        "message": record["message"],
        "timestamp": record["time"].timestamp(),
        "request_id": record["request_id"],
    }
    for key, value in record["extra"].items():
        if key not in simplified:
            simplified[key] = value
    serialized = json.dumps(simplified, default=str)
    print(serialized, file=sys.stdout)
```

The `default=str` keeps the JSON encoder from crashing on non-JSON-native values an endpoint might bind into extras later.

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_logging_sink.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/app/logging.py tests/test_logging_sink.py
git commit -m "feat(logging): serialize record.extra fields into JSON sink output"
```

---

## Task 6: Header-aware request_id + structured request log

**Files:**
- Modify: `src/app/middleware.py`
- Modify: `src/app/core/router.py` (drop `logger.debug` line)
- Modify: `src/app/v1/router.py` (drop `logger.debug` line)
- Test: `tests/test_request_log.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_request_log.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_request_log.py -v`
Expected: FAIL on at least the structured-log assertion (today's middleware emits two unstructured lines) and the inbound-header echo (today's middleware always overwrites).

- [ ] **Step 3: Update `src/app/middleware.py`**

Replace the file contents with:

```python
import time
import uuid

from fastapi import Request
from loguru import logger

from src.app.context import ctx_request_id


class RequestTimer:
    async def __call__(self, request: Request, call_next):
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.bind(
                method=request.method,
                path=request.url.path,
                status=500,
                duration_ms=round(duration_ms, 3),
                request_id=ctx_request_id.get(),
            ).exception("request")
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Process-Time"] = str(duration_ms / 1000.0)
        logger.bind(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 3),
            request_id=ctx_request_id.get(),
        ).info("request")
        return response


async def add_request_id(request: Request, call_next):
    incoming = request.headers.get("x-request-id")
    request_id = incoming if incoming else uuid.uuid4().hex
    ctx_request_id.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

Notes:
- `time.perf_counter()` is preferred over `time.time()` for durations.
- The header is canonicalized to `X-Request-ID` (Starlette compares header names case-insensitively, so this does not break existing readers).

- [ ] **Step 4: Drop the redundant `logger.debug` line in both routers**

In `src/app/core/router.py`, remove the line `logger.debug(f"Methode: {request.method} on {request.url.path}")` from `health_get` and `health_post`. The unused `logger` import can stay (still used by `health_ws`).

In `src/app/v1/router.py`, do the same removal.

- [ ] **Step 5: Run the request-log tests**

Run: `uv run pytest tests/test_request_log.py -v`
Expected: all four tests PASS.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/app/middleware.py src/app/core/router.py src/app/v1/router.py tests/test_request_log.py
git commit -m "feat(middleware): structured request log + header-aware X-Request-ID"
```

---

## Task 7: Liveness and readiness endpoints

**Files:**
- Modify: `src/app/core/schema.py`
- Modify: `src/app/core/router.py`
- Test: `tests/test_health.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from src.app.main import app


def test_liveness_returns_ok():
    with TestClient(app) as client:
        r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readiness_with_no_checks_is_ok():
    with TestClient(app) as client:
        # readiness_checks is initialized empty by lifespan
        r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"] == {}


def test_readiness_with_passing_check():
    async def ok_check():
        return True

    with TestClient(app) as client:
        app.state.readiness_checks.append(("db", ok_check))
        try:
            r = client.get("/health/ready")
        finally:
            app.state.readiness_checks.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"db": "ok"}


def test_readiness_with_failing_check():
    async def bad_check():
        return False

    with TestClient(app) as client:
        app.state.readiness_checks.append(("db", bad_check))
        try:
            r = client.get("/health/ready")
        finally:
            app.state.readiness_checks.clear()

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["checks"] == {"db": "fail"}


def test_readiness_with_raising_check_is_failed_not_500():
    async def boom():
        raise RuntimeError("connection refused")

    with TestClient(app) as client:
        app.state.readiness_checks.append(("db", boom))
        try:
            r = client.get("/health/ready")
        finally:
            app.state.readiness_checks.clear()

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["checks"] == {"db": "fail"}


def test_readiness_supports_sync_check():
    def sync_ok():
        return True

    with TestClient(app) as client:
        app.state.readiness_checks.append(("disk", sync_ok))
        try:
            r = client.get("/health/ready")
        finally:
            app.state.readiness_checks.clear()

    assert r.status_code == 200
    assert r.json()["checks"] == {"disk": "ok"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_health.py -v`
Expected: 404s for the new endpoints (or AttributeError on `readiness_checks`).

- [ ] **Step 3: Add response schemas**

In `src/app/core/schema.py`:

```python
from typing import Literal

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    version: str
    timestamp: float


class LivenessResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, Literal["ok", "fail"]]
```

- [ ] **Step 4: Add the endpoints**

In `src/app/core/router.py`, add to the imports:

```python
import asyncio
import inspect

from fastapi import Response

from src.app.core.schema import (
    HealthCheckResponse,
    LivenessResponse,
    ReadinessResponse,
)
```

(Drop the existing `from src.app.core.schema import HealthCheckResponse` in favor of the consolidated import. Keep `import asyncio` if it's already there.)

Then add the endpoints after the existing `/health` routes:

```python
@core.get("/health/live", response_model=LivenessResponse)
def health_live() -> LivenessResponse:
    return LivenessResponse(status="ok")


@core.get("/health/ready")
async def health_ready(request: Request, response: Response):
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
    statuses = {name: ("ok" if ok else "fail") for (name, _), ok in zip(checks, results)}
    overall = "ok" if all(results) else "degraded"
    response.status_code = 200 if overall == "ok" else 503
    return ReadinessResponse(status=overall, checks=statuses)
```

- [ ] **Step 5: Run the readiness tests**

Run: `uv run pytest tests/test_health.py -v`
Expected: all six tests PASS.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/app/core/router.py src/app/core/schema.py tests/test_health.py
git commit -m "feat(health): add /health/live and /health/ready with check registry"
```

---

## Task 8: Wire CORS conditionally

**Files:**
- Modify: `src/app/main.py`
- Test: `tests/test_cors.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cors.py`:

```python
from fastapi.testclient import TestClient

from src.app.config import Config
from src.app.main import get_application


def _base_config():
    """Build a Config copy whose `api_mode` we can mutate without leaking."""
    Config._toml_file = "config.toml"
    return Config()


def test_cors_disabled_by_default_no_preflight_headers():
    config = _base_config()
    config.api_mode.cors.enabled = False
    app = get_application(config)
    client = TestClient(app)

    r = client.options(
        "/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in {h.lower() for h in r.headers}


def test_cors_enabled_emits_preflight_headers():
    config = _base_config()
    config.api_mode.cors.enabled = True
    config.api_mode.cors.allow_origins = ["https://example.com"]
    config.api_mode.cors.allow_methods = ["GET", "POST"]
    config.api_mode.cors.allow_headers = ["*"]

    app = get_application(config)
    client = TestClient(app)

    r = client.options(
        "/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-foo",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "https://example.com"
    assert "GET" in r.headers.get("access-control-allow-methods", "")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_cors.py -v`
Expected: the enabled-case test FAILs (no CORS headers — middleware not added yet).

- [ ] **Step 3: Add CORS wiring in `get_application`**

In `src/app/main.py`, add:

```python
from fastapi.middleware.cors import CORSMiddleware
```

Inside `get_application`, before `application.middleware("http")(request_timer)`:

```python
cors = config.api_mode.cors
if cors.enabled:
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors.allow_origins,
        allow_methods=cors.allow_methods,
        allow_headers=cors.allow_headers,
        allow_credentials=cors.allow_credentials,
    )
```

`add_middleware` must be called before user middlewares for correct ordering (Starlette wraps each newly added middleware around the existing stack; CORS sits outermost so it can short-circuit preflights).

- [ ] **Step 4: Run the CORS tests**

Run: `uv run pytest tests/test_cors.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/app/main.py tests/test_cors.py
git commit -m "feat(cors): conditional CORS middleware wired from per-deployment config"
```

---

## Task 9: Dependency pattern scaffold

**Files:**
- Create: `src/app/dependencies.py`
- Test: `tests/test_dependencies.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_dependencies.py`:

```python
from types import SimpleNamespace

from fastapi import FastAPI, Request

from src.app.dependencies import get_resources


def test_get_resources_reads_from_app_state():
    request = type(
        "FakeReq",
        (),
        {"app": type("FakeApp", (), {"state": SimpleNamespace(resources=SimpleNamespace(http="http-client-sentinel"))})()},
    )()
    resources = get_resources(request)
    assert resources.http == "http-client-sentinel"


def test_get_resources_is_usable_as_fastapi_dependency():
    from fastapi import Depends
    from fastapi.testclient import TestClient

    from src.app.lifespan import lifespan

    app = FastAPI(lifespan=lifespan)

    @app.get("/probe")
    def probe(resources=Depends(get_resources)):
        # SimpleNamespace, set by lifespan
        return {"has_resources": resources is not None}

    with TestClient(app) as client:
        r = client.get("/probe")
    assert r.status_code == 200
    assert r.json() == {"has_resources": True}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_dependencies.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create `src/app/dependencies.py`**

```python
from fastapi import Request


def get_resources(request: Request):
    """Return the shared-resources namespace attached by lifespan.

    Add per-resource factories below this function. Each one should:
      1. read from `request.app.state.resources.<name>`
      2. export an `Annotated[Type, Depends(get_<name>)]` alias
    Tests can override factories with `app.dependency_overrides`.

    Template (uncomment when wiring a real client):

        # def get_http_client(request: Request) -> httpx.AsyncClient:
        #     return request.app.state.resources.http
        # HTTPClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]
    """
    return request.app.state.resources
```

- [ ] **Step 4: Run the dependency tests**

Run: `uv run pytest tests/test_dependencies.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/app/dependencies.py tests/test_dependencies.py
git commit -m "feat(dependencies): introduce get_resources factory and pattern docs"
```

---

## Task 10: Remove duplicated per-router error helpers

**Files:**
- Delete: `src/app/core/errors.py`
- Delete: `src/app/v1/errors.py`

- [ ] **Step 1: Confirm the files are unused**

Run: search the repo for any import of these modules.

```bash
uv run python -c "import subprocess; subprocess.run(['grep', '-rn', '--include=*.py', 'app.core.errors', 'src', 'tests'])"
uv run python -c "import subprocess; subprocess.run(['grep', '-rn', '--include=*.py', 'app.v1.errors', 'src', 'tests'])"
```

(Or simply use ripgrep / your editor's search.) Expected: no matches in `src/` or `tests/`.

- [ ] **Step 2: Delete the files**

```bash
git rm src/app/core/errors.py src/app/v1/errors.py
```

- [ ] **Step 3: Run the full suite**

Run: `uv run pytest -v`
Expected: all green — these files were not imported anywhere.

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor: drop unused per-router error helpers in favor of src/app/errors.py"
```

---

## Task 11: Final verification

- [ ] **Step 1: Run the entire test suite with coverage**

Run: `uv run python -m pytest --verbose --cov=./`
Expected: all tests pass; coverage on the new modules is reasonable (handlers, middleware, lifespan all exercised).

- [ ] **Step 2: Run ruff**

Run: `uv run ruff check src tests`
Expected: no errors.

- [ ] **Step 3: Smoke-run the app**

Run (in one shell): `FASTAPI_ENV=dev ./run_app.sh`
In another shell:

```bash
curl -i http://localhost:5000/health/live
curl -i http://localhost:5000/health/ready
curl -i -H 'X-Request-ID: smoke-1' http://localhost:5000/health
```

Expected:
- `/health/live` → 200, `{"status": "ok"}`.
- `/health/ready` → 200, `{"status": "ok", "checks": {}}`.
- The `/health` response echoes `X-Request-ID: smoke-1` and the server log shows a structured `request` line with `path=/health`, `status=200`, `request_id=smoke-1`.

Stop the server.

- [ ] **Step 4: Commit if anything was tweaked during smoke-test**

Otherwise no-op.
