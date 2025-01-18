#!/bin/sh

if [ "$FASTAPI_ENV" = "PROD" ]; then
	uv run uvicorn src.app.main:app --port 5000 --workers 2 --log-level "error"
elif [ "$FASTAPI_ENV" = "TEST" ]; then
	uv run pytest --cov-report html --cov=app tests
else
	 uv run uvicorn src.app.main:app --port 5000 --workers 1 --log-level "debug"
fi
