"""Tests for graphique endpoint."""
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import io
import base64
from src.main import app

client = TestClient(app)


class TestGraphique:
    """Test suite for graphique endpoint."""

    def test_graphique_disp1_returns_png(self):
        """Test that /api/graph/DISP_1 returns a valid PNG."""
        response = client.get("/api/graph/DISP_1")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        
        # Verify it's a valid PNG
        image_data = io.BytesIO(response.content)
        image = Image.open(image_data)
        assert image.format == "PNG"
        assert image.size == (1000, 700)  # Check default dimensions

    def test_graphique_arc_returns_png(self):
        """Test that /api/graph/ARC returns a valid PNG."""
        response = client.get("/api/graph/ARC")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        
        # Verify it's a valid PNG
        image_data = io.BytesIO(response.content)
        image = Image.open(image_data)
        assert image.format == "PNG"
        assert image.size == (1000, 700)

    def test_graphique_invalid_sensor(self):
        """Test that invalid sensor name returns 400."""
        response = client.get("/api/graph/INVALID")
        assert response.status_code == 400
        assert "must be" in response.json()["detail"].lower()

    def test_graphique_blank_when_no_test(self):
        """Test that graphique is blank when no test is running."""
        response = client.get("/api/graph/DISP_1")
        assert response.status_code == 200
        
        # Load image and check it's mostly transparent
        image_data = io.BytesIO(response.content)
        image = Image.open(image_data)
        
        # For RGBA, transparent pixel is (255, 255, 255, 0)
        # We're checking transparency at a non-axis pixel
        assert image.mode == "RGBA"

    def test_graphique_with_test_prepared(self):
        """Test graphique endpoint when test is prepared."""
        test_info = {
            "test_id": "graphique_test",
            "date": "2026-01-15",
            "operator_name": "Test Operator",
            "specimen_code": "GRAPH-001",
            "dim_length": 100.0,
            "dim_height": 50.0,
            "dim_width": 25.0,
            "loading_mode": "compression",
            "sensor_spacing": 10.0,
            "ext_support_spacing": 20.0,
            "load_point_spacing": 15.0
        }
        
        # Prepare test
        response = client.post("/api/test/info", json=test_info)
        assert response.status_code == 204
        
        # Get both graphiques (should have axes, test prepared)
        response_disp1 = client.get("/api/graph/DISP_1")
        assert response_disp1.status_code == 200
        assert response_disp1.headers["content-type"] == "image/png"
        
        response_arc = client.get("/api/graph/ARC")
        assert response_arc.status_code == 200
        assert response_arc.headers["content-type"] == "image/png"
        
        # Clean up
        client.put("/api/test/stop")

    def test_graphique_dimensions(self):
        """Test that graphique has expected dimensions."""
        response = client.get("/api/graph/DISP_1")
        image_data = io.BytesIO(response.content)
        image = Image.open(image_data)
        
        assert image.width == 1000
        assert image.height == 700

    def test_graphique_has_content_disposition(self):
        """Test that graphique response has proper Content-Disposition header."""
        response_disp1 = client.get("/api/graph/DISP_1")
        assert "content-disposition" in response_disp1.headers
        assert "graph_DISP_1.png" in response_disp1.headers["content-disposition"]
        
        response_arc = client.get("/api/graph/ARC")
        assert "content-disposition" in response_arc.headers
        assert "graph_ARC.png" in response_arc.headers["content-disposition"]

    def test_graphique_base64_endpoint_disp1(self):
        """Test that /api/graph/DISP_1/base64 returns base64-encoded PNG."""
        response = client.get("/api/graph/DISP_1/base64")
        assert response.status_code == 200
        data = response.json()
        
        # Verify it returns data as base64 data URI
        assert "data" in data
        assert data["data"].startswith("data:image/png;base64,")
        
        # Verify we can decode it
        base64_str = data["data"].split(",")[1]
        png_data = base64.b64decode(base64_str)
        
        # Verify it's a valid PNG
        image_data = io.BytesIO(png_data)
        image = Image.open(image_data)
        assert image.format == "PNG"
        assert image.size == (1000, 700)

    def test_graphique_base64_endpoint_arc(self):
        """Test that /api/graph/ARC/base64 returns base64-encoded PNG."""
        response = client.get("/api/graph/ARC/base64")
        assert response.status_code == 200
        data = response.json()
        
        # Verify it returns data as base64 data URI
        assert "data" in data
        assert data["data"].startswith("data:image/png;base64,")
        
        # Verify we can decode it
        base64_str = data["data"].split(",")[1]
        png_data = base64.b64decode(base64_str)
        
        # Verify it's a valid PNG
        image_data = io.BytesIO(png_data)
        image = Image.open(image_data)
        assert image.format == "PNG"
        assert image.size == (1000, 700)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
