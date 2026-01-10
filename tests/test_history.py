from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_history_list_endpoint() -> None:
    response = client.get("/api/history/list")
    assert response.status_code == 200
    data = response.json()
    assert "list" in data
    assert isinstance(data["list"], list)


def test_history_delete_endpoint() -> None:
    response = client.delete("/api/history/test_history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_history_put_endpoint() -> None:
    response = client.put("/api/history/test_history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_history_post_endpoint() -> None:
    response = client.post("/api/history/test_history", json=[{"field": "value"}])
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_history_get_fields() -> None:
    response = client.get("/api/history/test_history?download=false")
    assert response.status_code == 200
    data = response.json()
    assert "fields" in data
    assert isinstance(data["fields"], list)


def test_history_get_download() -> None:
    response = client.get("/api/history/test_history?download=true")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers.get("content-disposition", "")
