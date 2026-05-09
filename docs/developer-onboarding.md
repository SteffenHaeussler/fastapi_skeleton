# Developer onboarding

This project is a small FastAPI skeleton for stateless services. The default
local app port is `5000`.

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
