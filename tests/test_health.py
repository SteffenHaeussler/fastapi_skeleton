from fastapi.testclient import TestClient

from src.app.main import app


def test_liveness_returns_ok():
    with TestClient(app) as client:
        r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readiness_with_no_checks_is_ok():
    with TestClient(app) as client:
        r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"] == {}


def test_readiness_with_passing_check():
    async def ok_check():
        return True

    with TestClient(app) as client:
        app.state.readiness_checks.append(("db", ok_check))
        try:
            r = client.get("/health/ready")
        finally:
            app.state.readiness_checks.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"db": "ok"}


def test_readiness_with_failing_check():
    async def bad_check():
        return False

    with TestClient(app) as client:
        app.state.readiness_checks.append(("db", bad_check))
        try:
            r = client.get("/health/ready")
        finally:
            app.state.readiness_checks.clear()

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["checks"] == {"db": "fail"}


def test_readiness_with_raising_check_is_failed_not_500():
    async def boom():
        raise RuntimeError("connection refused")

    with TestClient(app) as client:
        app.state.readiness_checks.append(("db", boom))
        try:
            r = client.get("/health/ready")
        finally:
            app.state.readiness_checks.clear()

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["checks"] == {"db": "fail"}


def test_readiness_supports_sync_check():
    def sync_ok():
        return True

    with TestClient(app) as client:
        app.state.readiness_checks.append(("disk", sync_ok))
        try:
            r = client.get("/health/ready")
        finally:
            app.state.readiness_checks.clear()

    assert r.status_code == 200
    assert r.json()["checks"] == {"disk": "ok"}
