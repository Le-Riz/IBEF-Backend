from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_test_start_endpoint() -> None:
    response = client.put("/api/test/start", json=[{"field1": "value1"}, {"field2": "value2"}])
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_test_start_without_payload() -> None:
    response = client.put("/api/test/start")
    assert response.status_code == 200


def test_test_stop_endpoint() -> None:
    response = client.put("/api/test/stop")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
