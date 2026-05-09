from src.app.config import CORSConfig, Config


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
