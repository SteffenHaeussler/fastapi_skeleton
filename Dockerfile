# syntax=docker/dockerfile:1.7

#############################
# Shared deps layer (prod deps only, no project, no dev).
#############################
FROM python:3.12-slim AS deps

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

#############################
# Production build — installs the project on top of prod deps.
#############################
FROM deps AS build-prod

COPY src ./src
COPY run_app.sh config.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

#############################
# Test build — adds dev deps and tests on top of the same prod deps layer.
#############################
FROM deps AS build-test

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY src ./src
COPY tests ./tests
COPY run_app.sh ruff.toml config.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

#############################
# Test runtime — built with `docker build --target test ...`.
#############################
FROM python:3.12-slim AS test

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PATH="/app/.venv/bin:$PATH" \
    FASTAPI_ENV=TEST

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY --from=build-test /app /app

ENTRYPOINT ["bash", "./run_app.sh"]

#############################
# Runtime (prod) — default target (last stage). Lean: prod deps + project only.
#############################
FROM python:3.12-slim AS runtime

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY --from=build-prod /app /app

EXPOSE 5000

ENTRYPOINT ["bash", "./run_app.sh"]
