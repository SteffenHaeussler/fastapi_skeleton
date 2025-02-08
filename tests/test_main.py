from fastapi.testclient import TestClient

from src.app.main import app

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

    with client.websocket_connect("/ws/health") as websocket:
        data = websocket.receive_json()
        assert data["version"] == app.state.VERSION

        websocket.close(code=1000)

    with client.websocket_connect("/v1/ws/health") as websocket:
        data = websocket.receive_json()
        assert data["version"] == app.state.VERSION

        websocket.close(code=1000)
