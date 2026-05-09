# Developer onboarding

This project is a small FastAPI skeleton for stateless services. The default
local app port is `5000`.

## Project map

| Concern | File | Purpose |
| --- | --- | --- |
| Entry point | `src/app/main.py` | Builds the `FastAPI` app, wires lifespan, middleware, errors, routers |
| Lifespan | `src/app/lifespan.py` | Startup/shutdown; attaches resources, closers, readiness checks to `app.state` |
| Config | `src/app/config.py` | Loads deployment block from `config.toml` via `FASTAPI_ENV` |
| Routers | `src/app/core/router.py`, `src/app/v1/router.py` | Unversioned health/ws routes; versioned `v1` routes |
| Schemas | `src/app/core/schema.py`, `src/app/v1/schema.py` | Pydantic request/response models per router |
| Dependencies | `src/app/dependencies.py` | FastAPI `Depends` factories for shared resources |
| Errors | `src/app/errors.py` | Exception handlers and error response shape |
| Middleware | `src/app/middleware.py` | Request/response middleware (request id, request timing) |
| Logging | `src/app/logging.py` | Logger configuration and sinks |
| Observability | `src/app/observability.py` | Metrics/tracing setup |
| Runtime | `src/app/runtime.py` | Process-level runtime helpers |
| Context | `src/app/context.py` | Request-scoped context helpers |
| Meta | `src/app/meta.py` | App metadata (OpenAPI tags) |
| Tests | `tests/test_*.py` | One file per concern: `test_main`, `test_config`, `test_errors`, `test_cors`, `test_dependencies`, `test_health`, `test_lifespan`, `test_logging_sink`, `test_observability`, `test_request_log`, `test_runtime`, `test_websocket_logging` |

## First local run

Walk through these steps in order on a fresh clone. The service listens on
port `5000` by default.

1. **Install dependencies**

   ```bash
   uv sync
   ```

2. **Start the service**

   ```bash
   make run
   ```

   Leave this running in one terminal. Uvicorn logs the bound address on
   startup.

3. **Hit the health endpoints** (in a second terminal)

   ```bash
   curl -X GET "http://localhost:5000/health" -H "accept: application/json"
   curl -X GET "http://localhost:5000/v1/health" -H "accept: application/json"
   ```

   Both should return `200` with a JSON body. Stop the server with Ctrl-C
   when you're done.

4. **Run the tests**

   ```bash
   make test
   ```

   Runs pytest with coverage.

5. **Lint**

   ```bash
   make lint
   ```

   Runs `ruff check`. Use `make format` to auto-fix style issues.

## Local configuration

See `docs/configuration.md` for how `FASTAPI_ENV`, `config.toml`, `.env`, and
Compose fit together, and where each kind of setting belongs.

## Docker Compose

Run the service with Compose:

```bash
make up
```

Stop the Compose services:

```bash
make down
```

Compose reads `.env` automatically when present. `PORT` changes the host port;
the container still listens on port `5000`.

## Add a new endpoint

1. Add request and response models near the API version that owns the route,
   usually in `src/app/v1/schema.py`.
2. Add the route in `src/app/v1/router.py` using the shared `v1` router.
3. Always set `response_model` so FastAPI validates and documents the response.
4. Add focused tests for the route behavior and validation.

Example:

```python
from pydantic import BaseModel


class EchoRequest(BaseModel):
    message: str


class EchoResponse(BaseModel):
    message: str
```

```python
@v1.post("/echo", response_model=EchoResponse)
def echo(payload: EchoRequest) -> EchoResponse:
    return EchoResponse(message=payload.message)
```

## Handle errors

All HTTP error responses are wrapped by the handlers in `src/app/errors.py`.
The shared envelope has this shape:

```json
{
  "error": "snake_case_code",
  "message": "client-safe message",
  "status": 400,
  "request_id": "request-id",
  "details": null
}
```

Use FastAPI `HTTPException` for direct HTTP protocol failures inside route
handlers, such as bad input, forbidden access, or a missing resource when no
domain-specific exception exists.

```python
from fastapi import HTTPException


@v1.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, client: SomeClientDep) -> ItemResponse:
    item = await client.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return ItemResponse.model_validate(item)
```

Use `APIException` subclasses for app or domain errors that should keep a
stable status code, error code, optional details, and client-safe message.

```python
from src.app.errors import APIException


class ItemUnavailable(APIException):
    status_code = 409
    error_code = "item_unavailable"


@v1.post("/items/{item_id}/reserve", response_model=ItemResponse)
async def reserve_item(item_id: str, client: SomeClientDep) -> ItemResponse:
    item = await client.reserve(item_id)
    if item is None:
        raise ItemUnavailable(
            "item cannot be reserved",
            details={"item_id": item_id},
        )
    return ItemResponse.model_validate(item)
```

Do not rely on raw exception messages as user-facing output. Unexpected
exceptions are logged with the request ID and returned as a sanitized 500:

```json
{
  "error": "internal_server_error",
  "message": "Internal server error",
  "status": 500,
  "request_id": "request-id",
  "details": null
}
```

## Add a shared resource

Use the lifespan state for clients that need startup or shutdown, such as
database pools, HTTP clients, or model clients.

1. Create and attach the client in `src/app/lifespan.py` before `yield`.
2. Store it on `app.state.resources.<name>`.
3. Append async cleanup callables to `app.state._closers`.
4. Append readiness checks to `app.state.readiness_checks`.
5. Expose the resource through `src/app/dependencies.py`.
6. In tests, override the dependency factory with `app.dependency_overrides`.

Pseudo-DB example:

Use this as a copyable starting point for a real database pool/session/client.
`DatabaseClient` is pseudo-code; replace it with the concrete type and methods
from the database library used by your service.

Configuration:

```toml
[DEV]
CONFIG_NAME = "dev"
DEBUG = false
# database_url = "postgresql://app:secret@localhost:5432/app"
```

When turning this into real code, add the matching field to the config model
before reading `app.state.api_mode.database_url`.

Lifespan setup:

```python
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.resources = SimpleNamespace()
    app.state.readiness_checks = []
    app.state._closers = []

    db = DatabaseClient(app.state.api_mode.database_url)
    await db.connect()

    app.state.resources.db = db
    app.state._closers.append(db.aclose)
    app.state.readiness_checks.append(("db", db.ping))

    try:
        yield
    finally:
        for closer in reversed(app.state._closers):
            await closer()
```

Dependency factory:

```python
from typing import Annotated

from fastapi import Depends, Request


def get_db(request: Request) -> DatabaseClient:
    return request.app.state.resources.db


DBDep = Annotated[DatabaseClient, Depends(get_db)]
```

Router usage:

```python
@v1.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, db: DBDep) -> ItemResponse:
    item = await db.fetch_item(item_id)
    return ItemResponse.model_validate(item)
```

Test override:

```python
from fastapi.testclient import TestClient

from src.app.dependencies import get_db
from src.app.main import app


def test_get_item_uses_db_override():
    fake_db = FakeDatabaseClient(items={"abc": {"id": "abc", "name": "Example"}})
    app.dependency_overrides[get_db] = lambda: fake_db

    try:
        with TestClient(app) as client:
            response = client.get("/v1/items/abc")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == {"id": "abc", "name": "Example"}
```

## Request lifecycle

Every HTTP request flows through a fixed chain of middleware before it reaches
a route, and through the same chain in reverse on the way out. Starlette runs
the **last-added middleware first**, so the effective wrap order set up in
`src/app/main.py:46-58` is:

```
client → add_request_id → RequestTimer → prometheus_middleware → CORSMiddleware → route
```

### Request ID

`add_request_id` (`src/app/middleware.py:52`) reads the incoming
`x-request-id` header or generates a fresh `uuid4().hex`. It stores the id on
`request.state.request_id` and in the `ctx_request_id` ContextVar
(`src/app/context.py`) so any code — including the log sink — can read it
without threading the request through. The same id is echoed back as
`X-Request-ID` on every response, including error responses.

### Timing and request log

`RequestTimer` (`src/app/middleware.py:21`) measures wall time around
`call_next`, sets an `X-Process-Time` header (in seconds), and emits one
structured JSON log line per request:

```
method, path, status, duration_ms, request_id, trace_id, span_id
```

The JSON sink lives in `src/app/logging.py:39`. `trace_id` and `span_id` are
populated from the active OTel span when tracing is enabled. On unhandled
exceptions the timer logs `status=500` and re-raises so the registered
exception handlers still run.

### Error envelope

All errors return the same JSON shape (`ErrorResponse` in
`src/app/errors.py:12`):

```json
{
  "error": "validation_error",
  "message": "Request validation failed",
  "status": 422,
  "request_id": "…",
  "details": { "errors": [...] }
}
```

Four handlers are registered in `register_exception_handlers`:

- `HTTPException` — `error` is the snake-cased status phrase.
- `RequestValidationError` — `error="validation_error"`, status 422,
  `details.errors` from pydantic.
- `APIException` — the project's base class for app-specific errors. Subclass
  it to add domain errors:

  ```python
  from src.app.errors import APIException


  class ItemNotFound(APIException):
      status_code = 404
      error_code = "item_not_found"
  ```

- Bare `Exception` — logs the traceback and returns a generic 500 with no
  internal detail.

`_envelope` always sets `X-Request-ID` and re-applies CORS headers, because
FastAPI exception responses bypass `CORSMiddleware`.

### CORS

CORS is driven by `config.api_mode.cors` in `config.toml`. The middleware is
only added when `cors.enabled` is true (`src/app/main.py:46-54`); origins,
methods, headers, and credentials all come from config. Error responses
re-emit the matching headers manually so cross-origin clients still see the
JSON envelope.

### Observability hooks

`configure_observability` (`src/app/observability.py`) is called before routes
are mounted and toggles two independent features from the config block:

- **Prometheus** — registers a private `CollectorRegistry` with
  `http_requests_total` (Counter) and `http_request_duration_seconds`
  (Histogram), both labelled `(method, path, status)` where `path` is the
  matched route template to bound cardinality. Exposes the registry at the
  configured `metrics` path (default `/metrics`), excluded from OpenAPI.
- **OTel tracing** — installs a `TracerProvider` with `service.name` from
  config (only if one isn't already set) and calls
  `FastAPIInstrumentor().instrument_app(app)`, producing one span per
  request. The request log automatically picks up `trace_id`/`span_id`.

### Routing

`src/app/main.py:60-62` mounts:

- `core_router.core` at the root with tag `core` —
  `/health`, `/health/live`, `/health/ready`, `/ws/health`.
- `v1_router.v1` at `/v1` with tag `v1` — versioned health surface; this is
  where new versioned endpoints belong.

Tag metadata for the docs comes from `src/app/meta.py` via `openapi_tags`.

`/health/ready` (`src/app/core/router.py`) runs every check appended to
`app.state.readiness_checks` concurrently with `asyncio.gather` and returns
503 if any return false or raise. Websocket endpoints accept the connection,
push a `HealthCheckResponse` every 10 seconds, and log
`event="websocket.disconnect"` with the close code on disconnect.
