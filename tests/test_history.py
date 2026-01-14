from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_history_list_endpoint() -> None:
    """Test GET /api/history - list all histories"""
    response = client.get("/api/history")
    assert response.status_code == 200
    data = response.json()
    assert "list" in data
    assert isinstance(data["list"], list)


def test_history_get_metadata() -> None:
    """Test GET /api/history/{name} - get metadata (create test first)"""
    # First, create and then stop a test so it appears in history
    payload = {
        "test_id": "test_history",
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
    # Prepare test
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    # Start test
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    # Stop test
    stop_resp = client.put("/api/test/stop")
    assert stop_resp.status_code == 204
    
    # Now test history endpoint - list first to get the actual test_id with timestamp
    list_resp = client.get("/api/history")
    assert list_resp.status_code == 200
    histories = list_resp.json()["list"]
    assert len(histories) > 0
    
    # Get metadata of first (newest) test
    test_name = histories[0]
    response = client.get(f"/api/history/{test_name}")
    assert response.status_code == 200
    data = response.json()
    # Should return TestMetaData fields
    assert "test_id" in data
    assert "date" in data
    assert "operator_name" in data
    assert "specimen_code" in data
    assert "dim_length" in data
    assert "dim_height" in data
    assert "dim_width" in data
    assert "loading_mode" in data
    assert "sensor_spacing" in data
    assert "ext_support_spacing" in data
    assert "load_point_spacing" in data


def test_history_download() -> None:
    """Test GET /api/history/{name}/download - download ZIP"""
    # Create and stop a test
    payload = {
        "test_id": "test_download",
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
    client.post("/api/test/info", json=payload)
    client.put("/api/test/start")
    client.put("/api/test/stop")
    
    # Get test name from list
    list_resp = client.get("/api/history")
    histories = list_resp.json()["list"]
    if len(histories) == 0:
        return  # Skip if no tests available
    
    test_name = histories[0]
    response = client.get(f"/api/history/{test_name}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers.get("content-disposition", "")


def test_history_delete_endpoint() -> None:
    """Test DELETE /api/history/{name} - delete history"""
    # Create and stop a test
    payload = {
        "test_id": "test_delete",
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
    client.post("/api/test/info", json=payload)
    client.put("/api/test/start")
    client.put("/api/test/stop")
    
    # Get test name from list
    list_resp = client.get("/api/history")
    histories = list_resp.json()["list"]
    if len(histories) == 0:
        return  # Skip if no tests available
    
    test_name = histories[0]
    response = client.delete(f"/api/history/{test_name}")
    assert response.status_code == 204


def test_history_archive_endpoint() -> None:
    """Test PUT /api/history/{name}/archive - archive history"""
    # Create and stop a test
    payload = {
        "test_id": "test_archive",
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
    client.post("/api/test/info", json=payload)
    client.put("/api/test/start")
    client.put("/api/test/stop")
    
    # Get test name from list
    list_resp = client.get("/api/history")
    histories = list_resp.json()["list"]
    if len(histories) == 0:
        return  # Skip if no tests available
    
    test_name = histories[0]
    response = client.put(f"/api/history/{test_name}/archive")
    assert response.status_code == 204


def test_history_update_metadata() -> None:
    """Test PUT /api/history/{name} - update metadata"""
    # Create and stop a test
    payload = {
        "test_id": "test_update",
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
    client.post("/api/test/info", json=payload)
    client.put("/api/test/start")
    client.put("/api/test/stop")
    
    # Get test name from list
    list_resp = client.get("/api/history")
    histories = list_resp.json()["list"]
    if len(histories) == 0:
        return  # Skip if no tests available
    
    test_name = histories[0]
    
    metadata = {
        "test_id": test_name,
        "date": "2026-01-10",
        "operator_name": "Jane Doe",
        "specimen_code": "SPEC002",
        "dim_length": 150.0,
        "dim_height": 60.0,
        "dim_width": 30.0,
        "loading_mode": "tension",
        "sensor_spacing": 12.0,
        "ext_support_spacing": 25.0,
        "load_point_spacing": 18.0
    }
    response = client.put(f"/api/history/{test_name}", json=metadata)
    assert response.status_code == 204
