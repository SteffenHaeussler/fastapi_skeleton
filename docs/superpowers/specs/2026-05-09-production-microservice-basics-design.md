# Production Microservice Basics — Design

Adds production-grade scaffolding to the FastAPI skeleton: split liveness/readiness, central exception handlers with a stable error schema, structured request logging, off-by-default CORS, FastAPI lifespan, and a small shared-resource dependency pattern.

## Goals

- Operators can probe liveness and readiness independently.
- Every error response has the same shape, regardless of which handler produced it.
- Each request produces one structured log record with method, path, status, duration, request ID.
- CORS is configurable per deployment, off by default.
- A documented place exists for resources that need startup/shutdown (DB, HTTP, model clients) and for the dependency factories that expose them.

## Non-goals

- Wiring any concrete client (DB, HTTP, model). The skeleton ships empty; the spec documents the pattern only.
- Authentication, rate limiting, tracing, metrics. Out of scope.
- Migrating to RFC 7807 problem-details format.

---

## 1. Health endpoints

`src/app/core/router.py` gains two endpoints; existing `/health` GET/POST/WS at root and `/v1/health` are unchanged.

### `GET /health/live`

Always returns 200 if the process is responding. No external checks.

Response:
```json
{"status": "ok"}
```

Schema: `LivenessResponse(status: Literal["ok"])`.

### `GET /health/ready`

Iterates `app.state.readiness_checks` concurrently with `asyncio.gather(..., return_exceptions=True)`. Each check is a `Callable[[], Awaitable[bool] | bool]` paired with a name (a `(name, fn)` tuple).

- If all checks return truthy: status 200, body `{"status": "ok", "checks": {<name>: "ok", ...}}`.
- If any check returns falsy or raises: status 503, body `{"status": "degraded", "checks": {<name>: "ok"|"fail", ...}}`. Exception in a check counts as `"fail"`; the exception is logged but not surfaced to the response.

Schema: `ReadinessResponse(status: Literal["ok", "degraded"], checks: dict[str, Literal["ok", "fail"]])`.

The registry starts empty (set in lifespan). Code adding a resource may append a `(name, fn)` tuple.

---

## 2. Central exception handlers and error response schema

### `src/app/errors.py` (new, app-level)

Replaces `src/app/core/errors.py` and `src/app/v1/errors.py` (both deleted — they hold duplicate `bad_request` / `internal_server_error` / `forbidden` HTTPException helpers and a partial `APIException` that is never registered).

### `ErrorResponse` schema

```python
class ErrorResponse(BaseModel):
    error: str          # snake_case code, e.g. "bad_request", "validation_error"
    message: str        # human-readable
    status: int         # HTTP status
    request_id: str     # from ctx_request_id
    details: dict | None = None
```

All exception handlers return a `JSONResponse` whose body matches this schema.

### `APIException`

Kept as the base class for app-specific errors. Replaces the partial commented-out class in `v1/errors.py`.

```python
class APIException(Exception):
    status_code: int = 500
    error_code: str = "internal_server_error"

    def __init__(self, message: str, *, details: dict | None = None):
        self.message = message
        self.details = details
```

Subclasses override `status_code` and `error_code`. No subclasses are added in this change.

### Registered handlers

In `get_application`, after middleware registration:

| Exception                  | Status                   | `error` field                                     | Notes                                                                                                       |
| -------------------------- | ------------------------ | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `HTTPException`            | `exc.status_code`        | `HTTPStatus(status).phrase.lower().replace(" ", "_").replace("-", "_")`, e.g. `"bad_request"` | `message` from `exc.detail` if str, else `HTTPStatus(status).phrase`. `details` from `exc.detail` if dict, else None. |
| `RequestValidationError`   | 422                      | `"validation_error"`                              | `details = {"errors": exc.errors()}`. `message = "Request validation failed"`.                              |
| `APIException`             | `exc.status_code`        | `exc.error_code`                                  | `message = exc.message`, `details = exc.details`.                                                           |
| `Exception` (catch-all)    | 500                      | `"internal_server_error"`                         | `message = "Internal server error"` (do not leak `str(exc)`). Logs `logger.exception(...)` with request_id. |

`request_id` is always read from `ctx_request_id.get()`.

---

## 3. Request/response logging

Two middlewares kept, separated by concern.

### `add_request_id` (modified)

- Reads `X-Request-ID` from incoming headers; if absent or empty, generates `uuid4().hex`.
- Sets `ctx_request_id`.
- Sets the same value on the response header `X-Request-ID` (current code uses lowercase `x-request-id` — switch to canonical case).

### `RequestTimer` (modified)

- Records start time before `await call_next(request)`.
- After response: sets `X-Process-Time` header (kept as today, in seconds).
- Emits **one** structured INFO log record with the fields:
  ```json
  {"event": "request", "method": "GET", "path": "/v1/health", "status": 200, "duration_ms": 12.3, "request_id": "abc"}
  ```
- In normal operation, registered exception handlers convert exceptions into `JSONResponse` objects before they reach `RequestTimer`, so the timer logs at INFO with the handler's chosen status code (e.g. 500 for the catch-all). If `call_next` does raise (handler failure), the timer logs at ERROR with `status=500` via `logger.bind(...).exception("request")` and re-raises.

The two existing log lines (`"Incoming request"`, `"Processing this request took ... seconds"`) and the per-endpoint `logger.debug(f"Methode: {request.method} on {request.url.path}")` lines in both routers are removed.

### Log shape

The structured fields are passed via loguru `logger.bind(...).info("request")` so they appear in the `extra` of the record. `sink_serializer` in `src/app/logging.py` is updated to merge `record["extra"]` into the JSON output so the fields actually surface.

---

## 4. CORS

### Config

`config.toml` per-deployment block, optional:

```toml
[DEV.cors]
enabled = false
allow_origins = []
allow_methods = ["GET", "POST"]
allow_headers = ["*"]
allow_credentials = false
```

### Pydantic model

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

The `cors: CORSConfig = CORSConfig()` default means existing deployments without a `[X.cors]` section keep validating.

### Wiring

In `get_application`, only when `config.api_mode.cors.enabled` is true:

```python
application.add_middleware(
    CORSMiddleware,
    allow_origins=config.api_mode.cors.allow_origins,
    allow_methods=config.api_mode.cors.allow_methods,
    allow_headers=config.api_mode.cors.allow_headers,
    allow_credentials=config.api_mode.cors.allow_credentials,
)
```

When `enabled=false` (the default), `CORSMiddleware` is not added — CORS responses are not emitted at all.

---

## 5. Lifespan

`src/app/lifespan.py` (new):

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

`get_application` is changed to `FastAPI(lifespan=lifespan, openapi_tags=tags_metadata)`.

### Resource-add pattern (documented, not implemented)

To add a shared resource later:

1. Inside `lifespan`, before the `yield`:
   ```python
   client = SomeClient(...)
   await client.connect()
   app.state.resources.some = client
   app.state._closers.append(client.aclose)
   app.state.readiness_checks.append(("some", client.ping))
   ```
2. Add a `get_some` factory in `src/app/dependencies.py` (see §6).

---

## 6. Dependency pattern

`src/app/dependencies.py` (new):

```python
from typing import Annotated
from fastapi import Depends, Request

def get_resources(request: Request):
    return request.app.state.resources

# Template — uncomment and adapt when wiring a real client.
# def get_http_client(request: Request) -> httpx.AsyncClient:
#     return request.app.state.resources.http
# HTTPClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]
```

### Conventions

- One `get_<name>(request: Request) -> Client` per resource, reading from `request.app.state.resources.<name>`.
- Export an `Annotated[Client, Depends(get_<name>)]` alias next to it. Endpoints type-annotate parameters with the alias.
- Tests override with `app.dependency_overrides[get_<name>] = lambda: fake_client`.
- Factories live only in `dependencies.py`. Routers import the aliases.

---

## File map

| Path                                | Action                                                                  |
| ----------------------------------- | ----------------------------------------------------------------------- |
| `src/app/main.py`                   | Modify — register handlers, add CORS conditionally, pass `lifespan`.    |
| `src/app/middleware.py`             | Modify — `add_request_id` reads incoming header; `RequestTimer` logs structured record. |
| `src/app/logging.py`                | Modify — `sink_serializer` merges `record["extra"]`.                    |
| `src/app/config.py`                 | Modify — add `CORSConfig`, attach to `Deployment`.                      |
| `config.toml`                       | Modify — add empty `[X.cors]` (optional, defaults work without it).     |
| `src/app/errors.py`                 | New — `ErrorResponse`, `APIException`, handlers.                        |
| `src/app/lifespan.py`               | New — lifespan context manager.                                         |
| `src/app/dependencies.py`           | New — `get_resources`, template.                                        |
| `src/app/core/router.py`            | Modify — add `/health/live`, `/health/ready`. Drop `logger.debug` line. |
| `src/app/core/schema.py`            | Modify — add `LivenessResponse`, `ReadinessResponse`.                   |
| `src/app/core/errors.py`            | Delete.                                                                 |
| `src/app/v1/router.py`              | Modify — drop `logger.debug` line.                                      |
| `src/app/v1/errors.py`              | Delete.                                                                 |
| `tests/test_main.py`                | Modify — keep current assertions; add new tests below.                  |

## Test plan

Extend `tests/test_main.py` (or split into focused test files):

- `GET /health/live` returns 200 and `{"status": "ok"}`.
- `GET /health/ready` with no checks returns 200 and `{"status": "ok", "checks": {}}`.
- `GET /health/ready` with one passing check returns 200 with that check `"ok"`.
- `GET /health/ready` with one failing check returns 503 and `"degraded"`.
- Raising `HTTPException(400, "bad input")` from a test endpoint returns the `ErrorResponse` envelope with `error="bad_request"`, `status=400`, the request ID, and `message="bad input"`.
- A `RequestValidationError` returns 422 with `error="validation_error"` and `details.errors`.
- Raising a bare `Exception` returns 500 with `error="internal_server_error"` and `message="Internal server error"` (does not leak the original message).
- All error responses include a non-empty `request_id`.
- A request with an inbound `X-Request-ID: foo` header echoes `foo` on the response.
- A request without that header gets a generated request ID echoed back.
- With `cors.enabled=false`, an `OPTIONS` preflight does not produce CORS headers.
- With `cors.enabled=true` and an allowed origin, an `OPTIONS` preflight returns the configured `Access-Control-Allow-*` headers.

Existing tests for `/health`, `/v1/health`, `/ws/health`, `/v1/ws/health` continue to pass unchanged.

## Risks / notes

- Removing `src/app/core/errors.py` and `src/app/v1/errors.py` is safe: the helpers are not imported anywhere in `src/` (verified during exploration); the partial `APIException` in `v1/errors.py` is never registered.
- Switching from default `FastAPI()` to `FastAPI(lifespan=...)` deprecates `@app.on_event("startup"|"shutdown")` for this app, but no such hooks exist today.
- The structured request log replaces a per-endpoint `logger.debug`, which means endpoints that previously relied on that line for tracing now rely on the middleware log. Endpoint authors who want extra detail use `logger.bind(...).info(...)` directly.
