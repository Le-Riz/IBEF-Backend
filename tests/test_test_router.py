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
    # First prepare the test
    prep_response = client.post("/api/test/info", json=payload)
    assert prep_response.status_code == 204
    
    # Then start it
    response = client.put("/api/test/start")
    assert response.status_code == 204
    
    # Clean up
    client.put("/api/test/stop")


def test_test_start_without_payload() -> None:
    response = client.put("/api/test/start")
    # Starting without preparing first should return 400
    assert response.status_code == 400


def test_test_stop_endpoint() -> None:
    response = client.put("/api/test/stop")
    assert response.status_code == 204
