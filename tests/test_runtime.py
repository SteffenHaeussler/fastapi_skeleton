import pytest

from src.app import runtime
from src.app.runtime import RuntimeConfig, RuntimeConfigError, get_runtime_config


def test_runtime_config_defaults(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("WEB_CONCURRENCY", raising=False)

    assert get_runtime_config() == RuntimeConfig(port=5000, workers=2)


def test_runtime_config_reads_custom_values(monkeypatch):
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("WEB_CONCURRENCY", "4")

    assert get_runtime_config() == RuntimeConfig(port=8080, workers=4)


@pytest.mark.parametrize(
    ("env_name", "env_value"),
    [
        ("PORT", "abc"),
        ("PORT", "0"),
        ("PORT", "-1"),
        ("WEB_CONCURRENCY", "abc"),
        ("WEB_CONCURRENCY", "0"),
        ("WEB_CONCURRENCY", "-1"),
    ],
)
def test_runtime_config_rejects_invalid_positive_ints(
    monkeypatch, env_name, env_value
):
    monkeypatch.setenv(env_name, env_value)

    with pytest.raises(
        RuntimeConfigError, match=f"{env_name} must be a positive integer"
    ):
        get_runtime_config()


def test_main_starts_uvicorn_with_runtime_config(monkeypatch):
    calls = []
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    monkeypatch.setattr(
        runtime.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    runtime.main()

    assert calls == [
        (
            ("src.app.main:app",),
            {
                "host": "0.0.0.0",
                "port": 8080,
                "workers": 1,
                "log_level": "error",
            },
        )
    ]


def test_main_exits_on_invalid_runtime_config(monkeypatch, capsys):
    monkeypatch.setenv("PORT", "invalid")

    with pytest.raises(SystemExit) as exc_info:
        runtime.main()

    assert exc_info.value.code == 2
    assert "PORT must be a positive integer" in capsys.readouterr().err
