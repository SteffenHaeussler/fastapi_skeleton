
export FASTAPI_ENV="develop"
uvicorn app.main:app --port 5000 --reload --log-level "debug"
