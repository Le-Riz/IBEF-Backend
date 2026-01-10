from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_raw_point_endpoint() -> None:
    response = client.get("/api/raw/point/sensor456")
    assert response.status_code == 200
    data = response.json()
    assert "time" in data
    assert "value" in data
    assert isinstance(data["time"], (int, float))
    assert isinstance(data["value"], (int, float))
