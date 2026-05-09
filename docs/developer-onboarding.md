# Developer onboarding

This project is a small FastAPI skeleton for stateless services. The default
local app port is `5000`.

## Project map

| Concern | File | Purpose |
| --- | --- | --- |
| Entry point | `src/app/main.py` | Builds the app, wires lifespan, middleware, errors, routers |
| Lifespan | `src/app/lifespan.py` | Startup/shutdown resources, closers, readiness checks |
| Config | `src/app/config.py` | Loads `config.toml` deployment block selected by `FASTAPI_ENV` |
| Routers | `src/app/core/router.py`, `src/app/v1/router.py` | Core health/ws routes and versioned API routes |
| Schemas | `src/app/core/schema.py`, `src/app/v1/schema.py` | Pydantic request/response models |
| Dependencies | `src/app/dependencies.py` | FastAPI `Depends` factories for shared resources |
| Errors | `src/app/errors.py` | Exception handlers and error response envelope |
| Middleware | `src/app/middleware.py` | Request ID and request timing middleware |
| Logging | `src/app/logging.py` | Logger configuration and JSON sink |
| Observability | `src/app/observability.py` | Prometheus and OpenTelemetry setup |
| Runtime | `src/app/runtime.py` | Process-level runtime helpers |
| Context | `src/app/context.py` | Request-scoped context helpers |
| Meta | `src/app/meta.py` | OpenAPI tag metadata |
| Tests | `tests/test_*.py` | Focused tests by concern |

## First local run

Run these from a fresh clone:

```bash
uv sync
make run
```

In another terminal:

```bash
curl -X GET "http://localhost:5000/health" -H "accept: application/json"
curl -X GET "http://localhost:5000/v1/health" -H "accept: application/json"
make test
make lint
```

Both health calls should return `200` JSON responses. Stop the server with
Ctrl-C. `make lint` runs `ruff check`; `make format` auto-fixes style issues.

## Local configuration

See `docs/configuration.md` for how `FASTAPI_ENV`, `config.toml`, `.env`, and
Compose fit together.

Quick facts:

- `FASTAPI_ENV` values normalize to `DEV`, `STAGE`, `PROD`, or `TEST`.
- `PORT` and `WEB_CONCURRENCY` are runtime settings consumed by
  `src/app/runtime.py`.
- `PORT` and `WEB_CONCURRENCY` must be positive integers; invalid values print
  a runtime configuration error to stderr and exit with status `2`.

## Docker Compose

```bash
make up
make down
```

Compose reads `.env` automatically. `PORT` changes the host port; the container
still listens on `5000`. `WEB_CONCURRENCY` is passed through to the container
and controls uvicorn worker count. Dockerfile defaults are `FASTAPI_ENV=PROD`,
`PORT=5000`, and `WEB_CONCURRENCY=2`; Compose defaults `FASTAPI_ENV` to `DEV`
for local development.

## PR/update checklist

Run the same checks CI runs:

```bash
uv sync --locked --dev
uv run ruff check .
uv run ruff format --check .
uv run pytest --verbose --cov=./
uv build
```

For Docker, runtime configuration, health check, or startup changes, also run:

```bash
make docker-build
make up
curl -X GET "http://localhost:5000/health/live" -H "accept: application/json"
curl -X GET "http://localhost:5000/health/ready" -H "accept: application/json"
make down
```

`make test` and `make lint` are useful shortcuts, but CI also checks package
builds and ruff formatting.

### Dependency updates

Use `uv` as the source of truth:

```bash
uv add <package>
uv add --dev <package>
uv lock --upgrade-package <name>
uv lock --upgrade
uv lock --check
uv sync --locked --dev
```

Commit `pyproject.toml` and `uv.lock` together. Do not hand-edit `uv.lock` or
use `pip install` as the dependency source of truth.

### Common gotchas

- `make format` rewrites files; use `uv run ruff format --check .` for a
  read-only PR check.
- Runtime images install production dependencies only. Test, lint, and tooling
  packages belong in the dev dependency group.
- `FASTAPI_ENV` is stored uppercase in the supported config blocks.

## Add a new endpoint

Most application endpoints belong under `/v1`:

1. Add request/response models in `src/app/v1/schema.py`.
2. Import them in `src/app/v1/router.py`.
3. Add the route to the shared `v1` router with an explicit `response_model`.
4. Add focused `TestClient` tests for success, validation, and public response
   shape.

Minimal pattern:

```python
# src/app/v1/schema.py
from pydantic import BaseModel


class EchoRequest(BaseModel):
    message: str


class EchoResponse(BaseModel):
    message: str
```

```python
# src/app/v1/router.py
@v1.post("/echo", response_model=EchoResponse)
def echo(payload: EchoRequest) -> EchoResponse:
    return EchoResponse(message=payload.message)
```

```python
# tests/test_echo.py
from fastapi.testclient import TestClient

from src.app.main import app


def test_echo_returns_message():
    with TestClient(app) as client:
        response = client.post("/v1/echo", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


def test_echo_rejects_invalid_payload():
    with TestClient(app) as client:
        response = client.post("/v1/echo", json={})

    assert response.status_code == 422
```

## Handle errors

All HTTP error responses are wrapped by handlers in `src/app/errors.py`:

```json
{
  "error": "snake_case_code",
  "message": "client-safe message",
  "status": 400,
  "request_id": "request-id",
  "details": null
}
```

Use FastAPI `HTTPException` for direct HTTP protocol failures. Use
`APIException` subclasses for app/domain errors that need a stable status code,
error code, optional details, and client-safe message. Unexpected exceptions
are logged with the request ID and returned as sanitized
`internal_server_error` responses.

## Add a shared resource

Use lifespan state for clients that need startup/shutdown, such as database
pools, HTTP clients, or model clients:

1. Create and attach the client in `src/app/lifespan.py` before `yield`.
2. Store it on `app.state.resources.<name>`.
3. Append async cleanup callables to `app.state._closers`.
4. Append readiness checks to `app.state.readiness_checks`.
5. Expose the resource through a dependency in `src/app/dependencies.py`.
6. In tests, override the dependency with `app.dependency_overrides`.

If the resource needs configuration, add the setting in `src/app/config.py` and
`config.toml` before reading it from `app.state.api_mode`.

## Request lifecycle

Middleware order is defined in `src/app/main.py`. Starlette runs the last-added
middleware first, so HTTP requests flow through:

```text
client -> add_request_id -> RequestTimer -> prometheus_middleware -> CORSMiddleware -> route
```

Important behavior:

- Request ID: `add_request_id` reads `x-request-id` or generates one, stores it
  on `request.state.request_id`, sets the context var, and returns
  `X-Request-ID` on every response.
- Timing/logging: `RequestTimer` sets `X-Process-Time` and emits one JSON
  request log with method, path, status, duration, request ID, and trace/span
  IDs when tracing is active.
- Error envelope: registered handlers cover `HTTPException`,
  `RequestValidationError`, `APIException`, and bare `Exception`. Error
  responses also re-apply `X-Request-ID` and CORS headers.
- CORS: enabled only when `config.api_mode.cors.enabled` is true; origins,
  methods, headers, and credentials come from `config.toml`.
- Observability: Prometheus and tracing are disabled by default and enabled per
  deployment block in `config.toml`. Prometheus exposes the configured metrics
  path; tracing sets the OpenTelemetry service name from config.
- Routing: core routes live at `/health`, `/health/live`, `/health/ready`, and
  `/ws/health`; versioned routes include `/v1/health` and `/v1/ws/health`.
- Readiness: `/health/ready` runs all `app.state.readiness_checks`
  concurrently and returns `503` if any check fails or raises.
