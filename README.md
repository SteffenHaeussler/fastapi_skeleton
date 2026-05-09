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

See `docs/configuration.md` for how `FASTAPI_ENV`, `config.toml`, `.env`, and
Compose fit together. Local environment defaults are documented in `.env.example`.

## Running service in Docker

To build the Docker image:

`make docker-build`

(equivalent to `docker build -t "fastapi-api:latest" . --build-arg FASTAPI_ENV=dev`)

To run the Docker image:

```
docker run -p 5000:5000 -ti fastapi-api:latest
```

Or run the service with Docker Compose:

```
make up
```

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
