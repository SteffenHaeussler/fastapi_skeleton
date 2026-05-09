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

## Local setup

Install dependencies:

```bash
uv sync
```

Run the service:

```bash
make run
```

Run checks:

```bash
make test
make lint
```

`FASTAPI_ENV` selects a deployment block from `config.toml`. Valid values are
`DEV`, `STAGE`, `PROD`, and `TEST`. Copy `.env.example` to `.env` when using
Docker Compose locally; deployment settings such as `DEBUG` and CORS still live
in `config.toml`.

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

## Add a shared resource

Use the lifespan state for clients that need startup or shutdown, such as
database pools, HTTP clients, or model clients.

1. Create and attach the client in `src/app/lifespan.py` before `yield`.
2. Store it on `app.state.resources.<name>`.
3. Append async cleanup callables to `app.state._closers`.
4. Append readiness checks to `app.state.readiness_checks`.
5. Expose the resource through `src/app/dependencies.py`.
6. In tests, override the dependency factory with `app.dependency_overrides`.

Lifespan pattern:

```python
client = SomeClient(...)
await client.connect()

app.state.resources.some = client
app.state._closers.append(client.aclose)
app.state.readiness_checks.append(("some", client.ping))
```

Dependency pattern:

```python
from typing import Annotated

from fastapi import Depends, Request


def get_some_client(request: Request) -> SomeClient:
    return request.app.state.resources.some


SomeClientDep = Annotated[SomeClient, Depends(get_some_client)]
```

Router usage:

```python
@v1.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, client: SomeClientDep) -> ItemResponse:
    item = await client.get(item_id)
    return ItemResponse.model_validate(item)
```

Test override:

```python
app.dependency_overrides[get_some_client] = lambda: fake_client
```
