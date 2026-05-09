from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from src.app.context import ctx_request_id


class ErrorResponse(BaseModel):
    error: str
    message: str
    status: int
    request_id: str
    details: dict | None = None


class APIException(Exception):
    status_code: int = 500
    error_code: str = "internal_server_error"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


def _phrase_to_code(status: int) -> str:
    try:
        phrase = HTTPStatus(status).phrase
    except ValueError:
        return "http_error"
    return phrase.lower().replace(" ", "_").replace("-", "_")


def _status_phrase(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "HTTP error"


def _envelope(
    *,
    error: str,
    message: str,
    status: int,
    details: dict | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=error,
        message=message,
        status=status,
        request_id=ctx_request_id.get(),
        details=details,
    )
    return JSONResponse(status_code=status, content=payload.model_dump())


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    if isinstance(exc.detail, dict):
        message = _status_phrase(exc.status_code)
        details = exc.detail
    elif isinstance(exc.detail, str):
        message = exc.detail
        details = None
    else:
        message = _status_phrase(exc.status_code)
        details = None

    return _envelope(
        error=_phrase_to_code(exc.status_code),
        message=message,
        status=exc.status_code,
        details=details,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _envelope(
        error="validation_error",
        message="Request validation failed",
        status=422,
        details={"errors": exc.errors()},
    )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    return _envelope(
        error=exc.error_code,
        message=exc.message,
        status=exc.status_code,
        details=exc.details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception")
    return _envelope(
        error="internal_server_error",
        message="Internal server error",
        status=500,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
