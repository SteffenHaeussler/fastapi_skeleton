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


def _make_app():
    """Build a minimal app with our error setup wired in."""
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from pydantic import BaseModel

    from src.app.errors import APIException, register_exception_handlers
    from src.app.middleware import add_request_id

    app = FastAPI()
    app.middleware("http")(add_request_id)
    register_exception_handlers(app)

    class Body(BaseModel):
        x: int

    @app.get("/raise-http")
    def _raise_http():
        raise HTTPException(status_code=400, detail="bad input")

    @app.get("/raise-http-dict")
    def _raise_http_dict():
        raise HTTPException(status_code=403, detail={"reason": "nope"})

    @app.get("/raise-api")
    def _raise_api():
        class NotFound(APIException):
            status_code = 404
            error_code = "not_found"

        raise NotFound("missing", details={"id": 5})

    @app.get("/raise-bare")
    def _raise_bare():
        raise RuntimeError("internal secret leak attempt")

    @app.post("/validate")
    def _validate(body: Body):
        return body

    return TestClient(app, raise_server_exceptions=False)


def test_http_exception_returns_envelope():
    client = _make_app()
    r = client.get("/raise-http")
    assert r.status_code == 400
    body = r.json()
    assert body["error"] == "bad_request"
    assert body["message"] == "bad input"
    assert body["status"] == 400
    assert body["request_id"]
    assert body["details"] is None


def test_http_exception_with_dict_detail_uses_details():
    client = _make_app()
    r = client.get("/raise-http-dict")
    assert r.status_code == 403
    body = r.json()
    assert body["error"] == "forbidden"
    assert body["details"] == {"reason": "nope"}


def test_api_exception_uses_subclass_status_and_code():
    client = _make_app()
    r = client.get("/raise-api")
    assert r.status_code == 404
    body = r.json()
    assert body["error"] == "not_found"
    assert body["message"] == "missing"
    assert body["details"] == {"id": 5}


def test_validation_error_envelope():
    client = _make_app()
    r = client.post("/validate", json={"x": "not-an-int"})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validation_error"
    assert body["status"] == 422
    assert "errors" in body["details"]


def test_bare_exception_does_not_leak_message():
    client = _make_app()
    r = client.get("/raise-bare")
    assert r.status_code == 500
    body = r.json()
    assert body["error"] == "internal_server_error"
    assert body["message"] == "Internal server error"
    assert "secret leak" not in body["message"]
