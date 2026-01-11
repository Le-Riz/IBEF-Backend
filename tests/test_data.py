"""
Tests for sensor data endpoints - tests all available sensor IDs
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

# All valid sensor IDs
VALID_SENSOR_IDS = ["FORCE", "DISP_1", "DISP_2", "DISP_3"]


@pytest.mark.parametrize("sensor_id", VALID_SENSOR_IDS)
def test_sensor_data_endpoint(sensor_id: str) -> None:
    """Test GET /api/sensor/{sensor_id}/data - get latest data point for all sensors"""
    response = client.get(f"/api/sensor/{sensor_id}/data")
    assert response.status_code == 200
    data = response.json()
    assert "time" in data
    assert "value" in data
    assert isinstance(data["time"], (int, float))
    assert isinstance(data["value"], (int, float))


@pytest.mark.parametrize("sensor_id", VALID_SENSOR_IDS)
def test_sensor_data_history_endpoint(sensor_id: str) -> None:
    """Test GET /api/sensor/{sensor_id}/data/history - get historical data for all sensors"""
    response = client.get(f"/api/sensor/{sensor_id}/data/history?window=30")
    assert response.status_code == 409


@pytest.mark.parametrize("sensor_id", VALID_SENSOR_IDS)
def test_sensor_data_history_with_time_param(sensor_id: str) -> None:
    """Test GET /api/sensor/{sensor_id}/data/history with 600s window for all sensors"""
    response = client.get(f"/api/sensor/{sensor_id}/data/history?window=600")
    assert response.status_code == 409
