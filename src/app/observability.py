import time

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram
from prometheus_client.exposition import generate_latest


def configure_observability(app: FastAPI, deployment_config) -> None:
    observability = getattr(deployment_config, "observability", None)
    if observability is None:
        return

    if observability.prometheus.enabled:
        _configure_prometheus(app, observability.prometheus.path)

    if observability.tracing.enabled:
        _configure_tracing(app, observability.tracing.service_name)


def _configure_prometheus(app: FastAPI, metrics_path: str) -> None:
    registry = CollectorRegistry()
    request_counter = Counter(
        "http_requests_total",
        "Total HTTP requests.",
        ("method", "path", "status"),
        registry=registry,
    )
    request_duration = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds.",
        ("method", "path", "status"),
        registry=registry,
    )

    app.state.prometheus_registry = registry

    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        if request.url.path == metrics_path:
            return await call_next(request)

        start_time = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        path = _route_path(request)
        status = str(response.status_code)

        request_counter.labels(request.method, path, status).inc()
        request_duration.labels(request.method, path, status).observe(duration)
        return response

    @app.get(metrics_path, include_in_schema=False)
    def metrics():
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


def _configure_tracing(app: FastAPI, service_name: str) -> None:
    provider = trace.get_tracer_provider()
    if provider.__class__.__name__ == "ProxyTracerProvider":
        trace.set_tracer_provider(
            TracerProvider(
                resource=Resource.create(
                    {
                        "service.name": service_name,
                    }
                )
            )
        )

    FastAPIInstrumentor().instrument_app(app)


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return request.url.path
