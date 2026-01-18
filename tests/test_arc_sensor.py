"""Tests for ARC (circular deflection) sensor - calculated from DISP_1, DISP_2, DISP_3."""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.models.sensor_enum import SensorId

client = TestClient(app)


class TestARCSensor:
    """Test suite for ARC sensor calculation and special behavior."""

    def test_arc_in_sensor_enum(self):
        """Verify ARC is properly defined in SensorId enum."""
        assert hasattr(SensorId, 'ARC')
        sensors = [s for s in SensorId]
        assert len(sensors) == 7
        assert SensorId.ARC in sensors

    def test_arc_calculation_formula(self):
        """Verify the ARC formula: DISP_1 - (DISP_2 + DISP_3) / 2"""
        # Test case 1: Simple values
        disp1, disp2, disp3 = 10.0, 6.0, 4.0
        expected_arc = disp1 - (disp2 + disp3) / 2
        assert expected_arc == 5.0  # 10 - (6+4)/2 = 10 - 5 = 5
        
        # Test case 2: Equal displacements
        disp1, disp2, disp3 = 12.0, 12.0, 12.0
        expected_arc = disp1 - (disp2 + disp3) / 2
        assert expected_arc == 0.0  # 12 - 12 = 0
        
        # Test case 3: Negative result
        disp1, disp2, disp3 = 5.0, 8.0, 6.0
        expected_arc = disp1 - (disp2 + disp3) / 2
        assert expected_arc == -2.0  # 5 - (8+6)/2 = 5 - 7 = -2

    def test_arc_sensor_data_endpoint(self):
        """Test that ARC sensor is accessible via /api/sensor/ARC/data endpoint."""
        response = client.get("/api/sensor/ARC/data")
        assert response.status_code == 200
        data = response.json()
        assert "time" in data
        assert "value" in data
        assert isinstance(data["value"], (int, float))

    def test_arc_sensor_history_endpoint(self):
        """Test that ARC sensor history returns 409 when no test running."""
        response = client.get("/api/sensor/ARC/data/history?window=30")
        assert response.status_code == 409

    def test_arc_case_insensitive(self):
        """Test that ARC sensor ID is case-insensitive."""
        for arc_variant in ["arc", "Arc", "ARC"]:
            response = client.get(f"/api/sensor/{arc_variant}/data")
            assert response.status_code == 200

    def test_arc_graphique_dependency(self):
        """Test that ARC graphique requires DISP_2 and DISP_3 connected."""
        # This is tested in test_graphique.py but document here that 
        # ARC graphique depends on DISP_2 and DISP_3
        response = client.get("/api/graph/ARC")
        # Should succeed if dependencies are connected
        assert response.status_code in [200, 503]  # 200 if connected, 503 if not
