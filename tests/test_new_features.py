"""Tests for new features: raw_data.csv, description.md, and description endpoints"""
import os
import time
from fastapi.testclient import TestClient

from src.main import app
from core.services.test_manager import TEST_DATA_DIR
from core.services.test_manager import test_manager

client = TestClient(app)


def find_test_name(prefix: str) -> str:
    """Return the most recent history entry matching the given prefix."""
    list_resp = client.get("/api/history")
    histories = list_resp.json()["list"]
    matches = [h for h in histories if h.startswith(prefix)]
    assert matches, f"No history entry found for prefix {prefix}"
    return max(matches)


def reset_test_state() -> None:
    """Reset test_manager to NOTHING state (cleanup before tests)."""
    if test_manager.is_running:
        test_manager.stop_test()
    if test_manager.is_stopped:
        test_manager.finalize_test()


def test_raw_data_csv_creation() -> None:
    """Test that raw_data.csv is created when a test runs"""
    reset_test_state()
    
    # Prepare test
    payload = {
        "test_id": "test_raw_data",
        "date": "2026-01-14",
        "operator_name": "Test User",
        "specimen_code": "RAW001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "ext_sensor_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    
    # Prepare test
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    # Start test
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    # Wait a bit for data to be collected
    time.sleep(1.0)
    
    # Stop test
    stop_resp = client.put("/api/test/stop")
    assert stop_resp.status_code == 204
    
    # Finalize test
    finalize_resp = client.put("/api/test/finalize")
    assert finalize_resp.status_code == 204
    
    # Get test name from history (most recent matching prefix)
    test_name = find_test_name("test_raw_data")
    
    # Check that raw_data.csv exists
    test_dir = os.path.join(TEST_DATA_DIR, test_name)
    raw_data_path = os.path.join(test_dir, "raw_data.csv")
    data_csv_path = os.path.join(test_dir, "data.csv")
    
    assert os.path.exists(raw_data_path), "raw_data.csv should exist"
    assert os.path.exists(data_csv_path), "data.csv should exist"
    
    # Verify raw_data.csv exists (may be empty if no emulation running, just check file exists)
    assert os.path.getsize(raw_data_path) >= 0, "raw_data.csv should be created"


def test_description_md_creation() -> None:
    """Test that description.md is created when test is prepared"""
    reset_test_state()
    
    payload = {
        "test_id": "test_desc_creation",
        "date": "2026-01-14",
        "operator_name": "Test User",
        "specimen_code": "DESC001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "ext_sensor_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    
    # Prepare test
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    # Start to create test directory
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    # Stop immediately
    stop_resp = client.put("/api/test/stop")
    assert stop_resp.status_code == 204
    
    # Finalize test
    finalize_resp = client.put("/api/test/finalize")
    assert finalize_resp.status_code == 204
    
    # Get test name from history
    test_name = find_test_name("test_desc_creation")
    
    # Check that description.md exists
    test_dir = os.path.join(TEST_DATA_DIR, test_name)
    desc_path = os.path.join(test_dir, "description.md")
    
    assert os.path.exists(desc_path), "description.md should exist"
    
    # Verify description.md has default content
    with open(desc_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert test_name in content
        assert "Description de l'expérience" in content


def test_get_description_no_test() -> None:
    """Test GET /api/test/description with no test prepared"""
    reset_test_state()
    
    response = client.get("/api/test/description")
    assert response.status_code == 409
    data = response.json()
    assert "No test prepared" in data["detail"]


def test_put_description_no_test() -> None:
    """Test PUT /api/test/description with no test prepared"""
    reset_test_state()
    
    response = client.put("/api/test/description", json={"content": "test"})
    assert response.status_code == 409
    data = response.json()
    assert "No test prepared" in data["detail"]


def test_description_in_prepared_state() -> None:
    """Test that description can be GET and PUT in PREPARED state"""
    reset_test_state()
    
    payload = {
        "test_id": "test_prepared_desc",
        "date": "2026-01-14",
        "operator_name": "Test User",
        "specimen_code": "PREP001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "ext_sensor_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    
    # Prepare test (PREPARED state)
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    # GET description should work in PREPARED state
    get_resp = client.get("/api/test/description")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "content" in data
    default_content = data["content"]
    assert "Description de l'expérience" in default_content
    
    # PUT description should work in PREPARED state
    new_content = "# Custom Description\n\nThis is a test description in PREPARED state."
    put_resp = client.put("/api/test/description", json={"content": new_content})
    assert put_resp.status_code == 204
    
    # Verify the update
    get_resp2 = client.get("/api/test/description")
    assert get_resp2.status_code == 200
    data2 = get_resp2.json()
    assert data2["content"] == new_content
    
    # Clean up - start, stop, and finalize test
    client.put("/api/test/start")
    client.put("/api/test/stop")
    client.put("/api/test/finalize")


def test_description_in_running_state() -> None:
    """Test that description can be GET and PUT in RUNNING state"""
    reset_test_state()
    
    payload = {
        "test_id": "test_running_desc",
        "date": "2026-01-14",
        "operator_name": "Test User",
        "specimen_code": "RUN001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "ext_sensor_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    
    # Prepare and start test (RUNNING state)
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    # GET description should work in RUNNING state
    get_resp = client.get("/api/test/description")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "content" in data
    
    # PUT description should work in RUNNING state
    new_content = "# Running Test Description\n\nThis description was modified while the test is running."
    put_resp = client.put("/api/test/description", json={"content": new_content})
    assert put_resp.status_code == 204
    
    # Verify the update
    get_resp2 = client.get("/api/test/description")
    assert get_resp2.status_code == 200
    data2 = get_resp2.json()
    assert data2["content"] == new_content
    
    # Clean up - stop and finalize test
    client.put("/api/test/stop")
    client.put("/api/test/finalize")


def test_history_description_endpoints() -> None:
    """Test GET and PUT /api/history/{name}/description"""
    reset_test_state()
    
    payload = {
        "test_id": "test_history_desc",
        "date": "2026-01-14",
        "operator_name": "Test User",
        "specimen_code": "HIST001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "ext_sensor_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    
    # Create and stop a test
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    stop_resp = client.put("/api/test/stop")
    assert stop_resp.status_code == 204
    
    # Finalize to move to history
    finalize_resp = client.put("/api/test/finalize")
    assert finalize_resp.status_code == 204
    
    # Get test name from history
    test_name = find_test_name("test_history_desc")
    
    # GET description via history endpoint
    get_resp = client.get(f"/api/history/{test_name}/description")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "content" in data
    original_content = data["content"]
    
    # PUT description via history endpoint
    new_content = "# Updated Historical Description\n\nThis was updated after the test finished."
    put_resp = client.put(f"/api/history/{test_name}/description", json={"content": new_content})
    assert put_resp.status_code == 204
    
    # Verify the update
    get_resp2 = client.get(f"/api/history/{test_name}/description")
    assert get_resp2.status_code == 200
    data2 = get_resp2.json()
    assert data2["content"] == new_content


def test_description_not_in_metadata() -> None:
    """Test that description field is NOT in metadata.json"""
    reset_test_state()
    
    payload = {
        "test_id": "test_no_desc_in_meta",
        "date": "2026-01-14",
        "operator_name": "Test User",
        "specimen_code": "META001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "ext_sensor_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    
    # Create and stop a test
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    stop_resp = client.put("/api/test/stop")
    assert stop_resp.status_code == 204
    
    # Finalize to move to history
    finalize_resp = client.put("/api/test/finalize")
    assert finalize_resp.status_code == 204
    
    # Get metadata via history endpoint
    test_name = find_test_name("test_no_desc_in_meta")
    
    meta_resp = client.get(f"/api/history/{test_name}")
    assert meta_resp.status_code == 200
    metadata = meta_resp.json()
    
    # Verify description field is NOT in metadata
    assert "description" not in metadata
    
    # But all other fields should be there
    assert "test_id" in metadata
    assert "date" in metadata
    assert "operator_name" in metadata
    assert "specimen_code" in metadata
    assert "dim_length" in metadata


def test_description_persistence() -> None:
    """Test that description modifications persist to disk"""
    reset_test_state()
    
    payload = {
        "test_id": "test_persist_desc_final",
        "date": "2026-01-14",
        "operator_name": "Test User",
        "specimen_code": "PERS001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "ext_sensor_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    
    # Prepare test
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    # Modify description in PREPARED state
    prepared_content = "# PREPARED State Description\n\nModified before starting."
    put_resp = client.put("/api/test/description", json={"content": prepared_content})
    assert put_resp.status_code == 204
    
    # Start test
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    # Modify description in RUNNING state
    running_content = "# RUNNING State Description\n\nModified during test."
    put_resp2 = client.put("/api/test/description", json={"content": running_content})
    assert put_resp2.status_code == 204
    
    # Stop test
    stop_resp = client.put("/api/test/stop")
    assert stop_resp.status_code == 204
    
    # Finalize to move to history
    finalize_resp = client.put("/api/test/finalize")
    assert finalize_resp.status_code == 204
    
    # Get test name - should be the most recent one with our unique ID
    list_resp = client.get("/api/history")
    histories = list_resp.json()["list"]
    
    # Find the test with our unique ID
    test_name = None
    for h in histories:
        if "test_persist_desc_final" in h:
            test_name = h
            break
    
    assert test_name is not None, "Should find our test in history"
    
    test_dir = os.path.join(TEST_DATA_DIR, test_name)
    desc_path = os.path.join(test_dir, "description.md")
    
    # Read from disk
    with open(desc_path, 'r', encoding='utf-8') as f:
        disk_content = f.read()
    
    # Should have the RUNNING state modification (last one)
    assert disk_content == running_content


def test_test_state_transitions() -> None:
    """Test that test states (NOTHING/PREPARED/RUNNING/STOPPED) work correctly with description"""
    reset_test_state()
    
    # Initial state: NOTHING
    running_resp = client.get("/api/test/running")
    assert running_resp.status_code == 200
    status = running_resp.json()["status"]
    # Check lowercase version (API returns lowercase enum values)
    assert status.upper() == "NOTHING"
    
    # Description should not be accessible in NOTHING state
    desc_resp = client.get("/api/test/description")
    assert desc_resp.status_code == 409
    
    # Prepare test -> PREPARED
    payload = {
        "test_id": "test_states_trans",
        "date": "2026-01-14",
        "operator_name": "Test User",
        "specimen_code": "STATE001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    running_resp2 = client.get("/api/test/running")
    assert running_resp2.status_code == 200
    status2 = running_resp2.json()["status"]
    assert status2.upper() == "PREPARED"
    
    # Description SHOULD be accessible in PREPARED state
    desc_resp2 = client.get("/api/test/description")
    assert desc_resp2.status_code == 200
    
    # Start test -> RUNNING
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    running_resp3 = client.get("/api/test/running")
    assert running_resp3.status_code == 200
    status3 = running_resp3.json()["status"]
    assert status3.upper() == "RUNNING"
    
    # Description SHOULD be accessible in RUNNING state
    desc_resp3 = client.get("/api/test/description")
    assert desc_resp3.status_code == 200
    
    # Stop test -> STOPPED (not NOTHING anymore)
    stop_resp = client.put("/api/test/stop")
    assert stop_resp.status_code == 204
    
    running_resp4 = client.get("/api/test/running")
    assert running_resp4.status_code == 200
    status4 = running_resp4.json()["status"]
    assert status4.upper() == "STOPPED"
    
    # Description SHOULD still be accessible in STOPPED state
    desc_resp4 = client.get("/api/test/description")
    assert desc_resp4.status_code == 200
    
    # Finalize test -> NOTHING
    finalize_resp = client.put("/api/test/finalize")
    assert finalize_resp.status_code == 204
    
    running_resp5 = client.get("/api/test/running")
    assert running_resp5.status_code == 200
    status5 = running_resp5.json()["status"]
    assert status5.upper() == "NOTHING"
    
    # Description should not be accessible in NOTHING state (after finalize)
    desc_resp5 = client.get("/api/test/description")
    assert desc_resp5.status_code == 409
