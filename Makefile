.PHONY: help install test lint format run docker-build

IMAGE ?= fastapi-api:latest
FASTAPI_ENV ?= dev

help:
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-15s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Sync dependencies (including dev)
	uv sync

test: ## Run the test suite with coverage
	uv run pytest --verbose --cov=./

lint: ## Lint the codebase with ruff
	uv run ruff check .

format: ## Format the codebase with ruff
	uv run ruff format .
	uv run ruff check --fix .

run: ## Run the service locally
	FASTAPI_ENV=$(FASTAPI_ENV) ./run_app.sh

docker-build: ## Build the production Docker image
	docker build -t "$(IMAGE)" . --build-arg FASTAPI_ENV=$(FASTAPI_ENV)
