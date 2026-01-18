"""Tests to verify that API endpoints work correctly in emulation mode."""
import pytest
from fastapi.testclient import TestClient
from src.main import app
from core.sensor_reconnection import sensor_reconnection_manager


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestAPIEndpointsInEmulation:
    """Test that API endpoints return data (not 503) in emulation mode."""
    
    def test_sensor_data_endpoint_returns_200_in_emulation(self, client):
        """Test that /api/sensor/{sensor_id}/data returns 200 in emulation mode."""
        # Ensure emulation mode is enabled
        sensor_reconnection_manager.emulation_mode = True
        
        for sensor_id in ["FORCE", "DISP_1", "DISP_2", "DISP_3", "DISP_4", "DISP_5"]:
            response = client.get(f"/api/sensor/{sensor_id}/data")
            assert response.status_code == 200, \
                f"Sensor {sensor_id} should return 200 in emulation mode, got {response.status_code}"
    
    def test_sensor_raw_endpoint_returns_200_in_emulation(self, client):
        """Test that /api/sensor/{sensor_id}/raw returns 200 in emulation mode."""
        sensor_reconnection_manager.emulation_mode = True
        
        for sensor_id in ["FORCE", "DISP_1", "DISP_2", "DISP_3", "DISP_4", "DISP_5"]:
            response = client.get(f"/api/sensor/{sensor_id}/raw")
            assert response.status_code == 200, \
                f"Raw data for {sensor_id} should return 200 in emulation mode"
    
    def test_graphique_endpoints_return_200_in_emulation(self, client):
        """Test that /api/graph endpoints return 200 in emulation mode."""
        sensor_reconnection_manager.emulation_mode = True
        
        # Test DISP_1 graphique
        response = client.get("/api/graph/DISP_1")
        assert response.status_code == 200, \
            "DISP_1 graphique should return 200 in emulation mode"
        
        # Test ARC graphique
        response = client.get("/api/graph/ARC")
        assert response.status_code == 200, \
            "ARC graphique should return 200 in emulation mode"
    
    def test_graphique_base64_endpoints_return_200_in_emulation(self, client):
        """Test that /api/graph/{sensor_name}/base64 endpoints return 200 in emulation mode."""
        sensor_reconnection_manager.emulation_mode = True
        
        # Test DISP_1 base64
        response = client.get("/api/graph/DISP_1/base64")
        assert response.status_code == 200, \
            "DISP_1 base64 graphique should return 200 in emulation mode"
        
        # Test ARC base64
        response = client.get("/api/graph/ARC/base64")
        assert response.status_code == 200, \
            "ARC base64 graphique should return 200 in emulation mode"
    
    def test_never_returns_503_in_emulation(self, client):
        """Test that no data endpoints return 503 in emulation mode."""
        sensor_reconnection_manager.emulation_mode = True
        
        endpoints = [
            "/api/sensor/FORCE/data",
            "/api/sensor/DISP_1/data",
            "/api/sensor/FORCE/raw",
            "/api/sensor/DISP_1/raw",
            "/api/graph/DISP_1",
            "/api/graph/ARC",
            "/api/graph/DISP_1/base64",
            "/api/graph/ARC/base64",
            "/api/raw/point/FORCE",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code != 503, \
                f"Endpoint {endpoint} should NOT return 503 in emulation mode, got {response.status_code}"
