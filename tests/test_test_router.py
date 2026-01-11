from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_test_start_endpoint() -> None:
    payload = {
        "test_id": "test_001",
        "date": "2026-01-10",
        "operator_name": "John Doe",
        "specimen_code": "SPEC001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    response = client.put("/api/test/start", json=payload)
    assert response.status_code == 204


def test_test_start_without_payload() -> None:
    response = client.put("/api/test/start")
    # Starting while a test is already running should return conflict
    assert response.status_code == 409


def test_test_stop_endpoint() -> None:
    response = client.put("/api/test/stop")
    assert response.status_code == 204
