from fastapi.testclient import TestClient

from src.app.config import Config
from src.app.main import get_application


def _base_config():
    Config._toml_file = "config.toml"
    return Config()


def test_cors_disabled_by_default_no_preflight_headers():
    config = _base_config()
    config.api_mode.cors.enabled = False
    app = get_application(config)
    client = TestClient(app)

    r = client.options(
        "/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in {h.lower() for h in r.headers}


def test_cors_enabled_emits_preflight_headers():
    config = _base_config()
    config.api_mode.cors.enabled = True
    config.api_mode.cors.allow_origins = ["https://example.com"]
    config.api_mode.cors.allow_methods = ["GET", "POST"]
    config.api_mode.cors.allow_headers = ["*"]

    app = get_application(config)
    client = TestClient(app)

    r = client.options(
        "/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-foo",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "https://example.com"
    assert "GET" in r.headers.get("access-control-allow-methods", "")


def test_cors_enabled_applies_to_unhandled_500_envelope():
    config = _base_config()
    config.api_mode.cors.enabled = True
    config.api_mode.cors.allow_origins = ["https://example.com"]

    app = get_application(config)

    @app.get("/raise-bare")
    def _raise_bare():
        raise RuntimeError("internal secret leak attempt")

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/raise-bare", headers={"Origin": "https://example.com"})

    assert r.status_code == 500
    assert r.headers.get("access-control-allow-origin") == "https://example.com"
    assert r.json()["error"] == "internal_server_error"
