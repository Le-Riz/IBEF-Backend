"""Tests for sensor disconnection error handling in API endpoints."""

import pytest
from fastapi.testclient import TestClient
from core.models.sensor_enum import SensorId
from core.sensor_reconnection import sensor_reconnection_manager, SensorState
from src.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestSensorConnectionErrorHandling:
    """Test that endpoints return 503 when sensors are disconnected."""
    
    def test_get_sensor_data_returns_503_when_disconnected(self, client, hardware_mode):
        """GET /sensor/{sensor_id}/data should return 503 if sensor not connected."""
        # Set sensor as disconnected (hardware_mode ensures emulation doesn't override)
        if SensorId.FORCE in sensor_reconnection_manager.monitors:
            sensor_reconnection_manager.monitors[SensorId.FORCE].state = SensorState.DISCONNECTED
        
        response = client.get("/api/sensor/FORCE/data")
        assert response.status_code == 503
        assert "not connected" in response.json()["detail"]
    
    def test_get_sensor_raw_returns_503_when_disconnected(self, client, hardware_mode):
        """GET /sensor/{sensor_id}/raw should return 503 if sensor not connected."""
        # Set sensor as disconnected (hardware_mode ensures emulation doesn't override)
        if SensorId.FORCE in sensor_reconnection_manager.monitors:
            sensor_reconnection_manager.monitors[SensorId.FORCE].state = SensorState.DISCONNECTED
        
        response = client.get("/api/sensor/FORCE/raw")
        assert response.status_code == 503
        assert "not connected" in response.json()["detail"]
    
    def test_get_graphique_base64_returns_503_when_disp1_disconnected(self, client, hardware_mode):
        """GET /graph/{sensor_name}/base64 should return 503 if required sensors disconnected."""
        # Set DISP_1 as disconnected (hardware_mode ensures emulation doesn't override)
        if SensorId.DISP_1 in sensor_reconnection_manager.monitors:
            sensor_reconnection_manager.monitors[SensorId.DISP_1].state = SensorState.DISCONNECTED
        
        response = client.get("/api/graph/DISP_1/base64")
        assert response.status_code == 503
        assert "DISP_1" in response.json()["detail"]
    
    def test_get_graphique_arc_returns_503_when_disp2_disconnected(self, client, hardware_mode):
        """GET /graph/ARC should return 503 if DISP_2 not connected."""
        # Set DISP_2 as disconnected (hardware_mode ensures emulation doesn't override)
        if SensorId.DISP_2 in sensor_reconnection_manager.monitors:
            sensor_reconnection_manager.monitors[SensorId.DISP_2].state = SensorState.DISCONNECTED
        
        response = client.get("/api/graph/ARC")
        assert response.status_code == 503
        assert "DISP_2" in response.json()["detail"] or "DISP_3" in response.json()["detail"]
    

        assert "not connected" in response.json()["detail"]
