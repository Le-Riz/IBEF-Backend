from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_data_point_endpoint() -> None:
    response = client.get("/api/data/point/sensor123")
    assert response.status_code == 200
    data = response.json()
    assert "time" in data
    assert "value" in data
    assert isinstance(data["time"], (int, float))
    assert isinstance(data["value"], (int, float))


def test_data_list_endpoint() -> None:
    response = client.get("/api/data/list/sensor123")
    assert response.status_code == 200
    data = response.json()
    assert "list" in data
    assert isinstance(data["list"], list)
    if len(data["list"]) > 0:
        assert "time" in data["list"][0]
        assert "value" in data["list"][0]


def test_data_list_with_time_param() -> None:
    response = client.get("/api/data/list/sensor123?time=100.5")
    assert response.status_code == 200
    data = response.json()
    assert "list" in data
