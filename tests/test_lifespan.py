from fastapi.testclient import TestClient

from src.app.main import app


def test_lifespan_initializes_state_slots():
    with TestClient(app) as client:
        client.get("/health")
        assert hasattr(app.state, "resources")
        assert hasattr(app.state, "readiness_checks")
        assert hasattr(app.state, "_closers")
        assert app.state.readiness_checks == []
        assert app.state._closers == []
