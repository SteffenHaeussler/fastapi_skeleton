# fastapi_skeleton

Simple fastapi skeleton for a stateless microservice (application for ml models, optimization, ...)

## Running service manually

To run the service manually in debug mode install the required python dependencies:

`uv sync`

You can run the service in debug mode:

```
export FASTAPI_ENV="dev"
./run_app.sh
```

Or via the Makefile:

```
make run
```

Local environment defaults are documented in `.env.example`.

## Running service in Docker

To build the Docker image:

`make docker-build`

(equivalent to `docker build -t "fastapi-api:latest" . --build-arg FASTAPI_ENV=dev`)

To run the Docker image:

```
docker run -p 5000:5000 -ti fastapi-api:latest
```

Runtime settings are read from environment variables:

- `PORT` controls the uvicorn listen port inside the container. It defaults to
  `5000` and must be a positive integer.
- `WEB_CONCURRENCY` controls the uvicorn worker count. It defaults to `2` and
  must be a positive integer.

For direct `docker run`, keep the host/container port mapping aligned with
`PORT` when you change it:

```
docker run -e PORT=8080 -e WEB_CONCURRENCY=4 -p 8080:8080 -ti fastapi-api:latest
```

Or run the service with Docker Compose:

```
make up
```

Compose reads `.env` automatically. In Compose, `PORT` changes only the host
port mapped to container port `5000`; the container still listens on `5000`.
`WEB_CONCURRENCY` is passed through to the container worker count.

To stop the Compose services:

```
make down
```

## Local querying

To check that the service is alive, run:

`curl -X GET "http://localhost:5000/health" -H  "accept: application/json"`

`curl -X GET "http://localhost:5000/v1/health" -H  "accept: application/json"`

For the websockets endpoint, run:

`websocat ws://127.0.0.1:5000/ws/health`

`websocat ws://127.0.0.1:5000/v1/ws/health`

## Observability

The service emits structured JSON request logs. Each completed HTTP request
logs one record with `message="request"` plus `method`, `path`, `status`,
`duration_ms`, and `request_id`. When tracing is enabled and a span is active,
the request log also includes `trace_id` and `span_id`.

Incoming `X-Request-ID` values are echoed on the response. If the request does
not provide one, the service generates an ID and returns it as `X-Request-ID`.
Responses also include `X-Process-Time`, measured in seconds.

Prometheus and tracing are disabled by default and are enabled per deployment
block in `config.toml`:

```toml
[DEV.observability.prometheus]
enabled = true
path = "/metrics"

[DEV.observability.tracing]
enabled = true
service_name = "fastapi_skeleton"
```

Prometheus exposes metrics at the configured path, defaulting to `/metrics`.
Tracing uses the configured `service_name` as the OpenTelemetry service name.

## API Documentation

The user interface for the API is defined in `http://localhost:5000/docs` endpoint.
Be aware, that OpenAPI schema doesn't support websockets.

## Testing

To run the tests:

`make test`

(equivalent to `uv run python -m pytest --verbose --cov=./`)

## Lint and format

```
make lint
make format
```

## Available make targets

Run `make help` to see all available targets.

## Developer onboarding

See `docs/developer-onboarding.md` for local setup notes and the recipe for
adding a new endpoint or shared resource.
