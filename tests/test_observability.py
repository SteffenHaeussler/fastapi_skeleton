from fastapi import APIRouter
from fastapi.testclient import TestClient

from src.app.config import Config
from src.app.main import get_application


def _base_config():
    Config._toml_file = "config.toml"
    return Config()


def test_metrics_endpoint_is_not_registered_when_prometheus_disabled():
    config = _base_config()
    config.api_mode.observability.prometheus.enabled = False
    app = get_application(config)

    with TestClient(app) as client:
        r = client.get("/metrics")

    assert r.status_code == 404


def test_metrics_endpoint_is_root_only_and_counts_root_and_v1_routes():
    config = _base_config()
    config.api_mode.observability.prometheus.enabled = True
    app = get_application(config)

    with TestClient(app) as client:
        client.get("/health")
        client.get("/v1/health")
        metrics = client.get("/metrics")
        v1_metrics = client.get("/v1/metrics")

    assert metrics.status_code == 200
    assert "text/plain" in metrics.headers["content-type"]
    assert v1_metrics.status_code == 404

    body = metrics.text
    assert 'http_requests_total{method="GET",path="/health",status="200"} 1.0' in body
    assert (
        'http_requests_total{method="GET",path="/v1/health",status="200"} 1.0' in body
    )
    assert 'path="/metrics"' not in body


def test_tracing_enabled_instruments_fastapi_app(monkeypatch):
    calls = []

    class FakeInstrumentor:
        def instrument_app(self, app):
            calls.append(app)

    monkeypatch.setattr(
        "src.app.observability.FastAPIInstrumentor",
        lambda: FakeInstrumentor(),
    )

    config = _base_config()
    config.api_mode.observability.tracing.enabled = True
    app = get_application(config)

    assert calls == [app]


def test_traceparent_propagates_to_route_when_tracing_enabled():
    from opentelemetry import trace

    config = _base_config()
    config.api_mode.observability.tracing.enabled = True
    app = get_application(config)
    router = APIRouter()

    @router.get("/trace-context")
    def trace_context():
        span_context = trace.get_current_span().get_span_context()
        return {
            "trace_id": format(span_context.trace_id, "032x"),
            "span_id": format(span_context.span_id, "016x"),
            "is_valid": span_context.is_valid,
        }

    app.include_router(router)

    with TestClient(app) as client:
        r = client.get(
            "/trace-context",
            headers={
                "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
            },
        )

    assert r.status_code == 200
    assert r.json()["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert r.json()["is_valid"] is True
