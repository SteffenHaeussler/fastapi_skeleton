#!/bin/sh


if [ "$FASTAPI_ENV" = "prod" ]; then
	uvicorn app.main:app --port 5000 --workers 2 --log-level "error"
elif [ "$FASTAPI_ENV" = "testing" ]; then
	pytest --cov-report html --cov=app app/tests
else
	 uvicorn app.main:app --port 5000 --workers 2 --log-level "debug"
fi
