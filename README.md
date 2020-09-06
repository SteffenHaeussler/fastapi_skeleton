# fastapi_skeleton
Simple fastapi skeleton for a stateless microservice (application for ml models, optimization, ...)


## Running service manually

To run the service manually in debug mode install the required python dependencies:

 `pip install -r requirements.txt`

You can run the service in debug mode without gunicorn:

`./run_debug.sh`

## Running service in Docker

To build the Docker image:

`docker build -t "fastapi-api:latest" . --build-arg FASTAPI_ENV=develop`

To run the Docker image:

```
docker run \
  -p 5000:5000 -ti fastapi-api:latest
```

## Local querying

To check that the service is alive, run:

`curl -X GET "http://localhost:5000/health" -H  "accept: application/json"`

`curl -X GET "http://localhost:5000/v1/health" -H  "accept: application/json"`

## API Documentation

The user interface for the API is defined in `http://localhost:5000/docs` endpoint.


## Testing

To run the tests:

  `python -m pytest --verbose --cov=./`
