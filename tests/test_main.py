from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_read_main():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == app.state.VERSION

    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["version"] == app.state.VERSION

    response = client.post("/health")
    assert response.status_code == 200
    assert response.json()["version"] == app.state.VERSION

    response = client.post("/v1/health")
    assert response.status_code == 200
    assert response.json()["version"] == app.state.VERSION
