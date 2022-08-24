
export FASTAPI_ENV="develop"
poetry run uvicorn app.main:app --port 5000 --reload --log-level "debug"
