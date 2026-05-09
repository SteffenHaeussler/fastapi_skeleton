import pytest
from pydantic import ValidationError

from src.app.config import CORSConfig, Config, Deployment


def test_cors_config_defaults_disabled():
    cors = CORSConfig()
    assert cors.enabled is False
    assert cors.allow_origins == []
    assert cors.allow_methods == ["GET", "POST"]
    assert cors.allow_headers == ["*"]
    assert cors.allow_credentials is False


def test_deployment_has_default_cors_config():
    config = Config()
    assert config.DEV.cors.enabled is False
    assert config.PROD.cors.enabled is False


def test_api_mode_returns_selected_deployment(monkeypatch):
    monkeypatch.setenv("FASTAPI_ENV", "STAGE")
    config = Config()

    assert isinstance(config.api_mode, Deployment)
    assert config.api_mode == config.STAGE


def test_fastapi_env_normalizes_lowercase_before_api_mode_lookup(monkeypatch):
    monkeypatch.setenv("FASTAPI_ENV", "stage")
    config = Config()

    assert config.FASTAPI_ENV == "STAGE"
    assert config.api_mode == config.STAGE


def test_invalid_fastapi_env_fails_during_config_construction(monkeypatch):
    monkeypatch.setenv("FASTAPI_ENV", "bad")

    with pytest.raises(
        ValidationError,
        match="Invalid FASTAPI_ENV 'BAD'. Expected one of: DEV, PROD, STAGE, TEST",
    ):
        Config()
