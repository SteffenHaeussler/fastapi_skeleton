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
