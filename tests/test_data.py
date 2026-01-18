"""
Tests for basic sensor data endpoints - tests all available sensor IDs using parametrize.
More specific tests (raw data, zero calibration) are in test_sensor.py
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

# All valid sensor IDs
VALID_SENSOR_IDS = ["FORCE", "DISP_1", "DISP_2", "DISP_3", "DISP_4", "DISP_5"]


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


def test_sensor_data_invalid_id() -> None:
    """Test GET /api/sensor/{sensor_id}/data with invalid sensor ID returns 400"""
    response = client.get("/api/sensor/INVALID_SENSOR/data")
    assert response.status_code == 400
    data = response.json()
    assert "Invalid sensor_id" in data["detail"]


def test_sensor_data_case_insensitive() -> None:
    """Test that sensor IDs are case-insensitive"""
    response = client.get("/api/sensor/force/data")
    assert response.status_code == 200
    data = response.json()
    assert "time" in data
    assert "value" in data


@pytest.mark.parametrize("sensor_id", VALID_SENSOR_IDS)
def test_sensor_data_history_endpoint(sensor_id: str) -> None:
    """Test GET /api/sensor/{sensor_id}/data/history - get historical data for all sensors"""
    response = client.get(f"/api/sensor/{sensor_id}/data/history?window=30")
    assert response.status_code == 409  # No test running


@pytest.mark.parametrize("sensor_id", VALID_SENSOR_IDS)
def test_sensor_data_history_with_time_param(sensor_id: str) -> None:
    """Test GET /api/sensor/{sensor_id}/data/history with 600s window for all sensors"""
    response = client.get(f"/api/sensor/{sensor_id}/data/history?window=600")
    assert response.status_code == 409  # No test running


def test_sensor_data_history_invalid_window() -> None:
    """Test GET /api/sensor/{sensor_id}/data/history with invalid window returns 400"""
    response = client.get("/api/sensor/FORCE/data/history?window=10")
    assert response.status_code == 400
    data = response.json()
    assert "Invalid window" in data["detail"]


def test_sensor_data_history_invalid_id() -> None:
    """Test GET /api/sensor/{sensor_id}/data/history with invalid sensor ID returns 400"""
    response = client.get("/api/sensor/INVALID_SENSOR/data/history")
    assert response.status_code == 400
    data = response.json()
    assert "Invalid sensor_id" in data["detail"]
