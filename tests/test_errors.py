import pytest

from src.app.errors import APIException, ErrorResponse


def test_error_response_schema_fields():
    e = ErrorResponse(
        error="bad_request",
        message="bad input",
        status=400,
        request_id="abc",
    )
    dumped = e.model_dump()
    assert dumped == {
        "error": "bad_request",
        "message": "bad input",
        "status": 400,
        "request_id": "abc",
        "details": None,
    }


def test_api_exception_defaults():
    exc = APIException("boom")
    assert exc.status_code == 500
    assert exc.error_code == "internal_server_error"
    assert exc.message == "boom"
    assert exc.details is None


def test_api_exception_subclass_overrides():
    class NotFound(APIException):
        status_code = 404
        error_code = "not_found"

    exc = NotFound("missing", details={"id": 5})
    assert exc.status_code == 404
    assert exc.error_code == "not_found"
    assert exc.details == {"id": 5}
