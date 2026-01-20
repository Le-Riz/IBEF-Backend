"""Test that stop() immediately stops all data recording and schema updates."""

import os
import time
from fastapi.testclient import TestClient

from src.main import app
from core.services.test_manager import test_manager
from core.models.sensor_enum import SensorId

client = TestClient(app)


def reset_test_state() -> None:
    """Reset test_manager to NOTHING state (cleanup before tests)."""
    if test_manager.is_running:
        test_manager.stop_test()
    if test_manager.is_stopped:
        test_manager.finalize_test()


def test_stop_prevents_callbacks() -> None:
    """Test that after stop(), is_running is False preventing further callbacks."""
    reset_test_state()
    
    payload = {
        "test_id": "test_stop_callbacks",
        "date": "2026-01-18",
        "operator_name": "Test User",
        "specimen_code": "STOP001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "ext_sensor_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    
    # Prepare and start test
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    # Verify test is running
    assert test_manager.is_running is True, "Test should be running"
    assert test_manager.is_stopped is False, "Test should not be stopped"
    
    # Stop test
    stop_resp = client.put("/api/test/stop")
    assert stop_resp.status_code == 204
    
    # Verify test is stopped
    assert test_manager.is_running is False, "Test should not be running after stop"
    assert test_manager.is_stopped is True, "Test should be stopped"
    
    # Try to emit a fake processed data frame
    # This callback should NOT update anything because is_running=False
    fake_frame = {
        "timestamp": time.time(),
        "values": {
            SensorId.FORCE.value: 42.0,
            SensorId.DISP_1.value: 1.5,
            SensorId.DISP_2.value: 1.6,
            SensorId.DISP_3.value: 1.7,
            SensorId.DISP_4.value: 1.55,
            SensorId.DISP_5.value: 1.45,
            SensorId.ARC.value: 1.6,
        }
    }
    
    # Get initial circular buffer state
    initial_buffer_size = test_manager.data_storage.buffers[SensorId.FORCE.value].count
    
    # Trigger the callback manually (simulating what event_hub would do)
    test_manager._on_processed_data("processed_data", fake_frame)
    
    # Buffer size should NOT increase
    final_buffer_size = test_manager.data_storage.buffers[SensorId.FORCE.value].count
    assert final_buffer_size == initial_buffer_size, \
        f"Buffer was updated after stop: {initial_buffer_size} → {final_buffer_size}"
    
    # Clean up
    client.put("/api/test/finalize")


def test_stop_closes_file_handles() -> None:
    """Test that stop() sets file handles to None (preventing further writes)."""
    reset_test_state()
    
    payload = {
        "test_id": "test_stop_files",
        "date": "2026-01-18",
        "operator_name": "Test User",
        "specimen_code": "FILES001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "ext_sensor_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    
    # Prepare and start test
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    # Collect data for 1+ second to ensure files are created and data written
    time.sleep(1.5)
    
    # Files should be open or None (depending on if data arrived)
    # The important thing is they're not closed (ValueError if writing to closed file)
    
    # Stop test
    stop_resp = client.put("/api/test/stop")
    assert stop_resp.status_code == 204
    
    # Verify all file handles are set to None
    # This prevents any further writes (trying to write to None would raise AttributeError)
    assert test_manager.raw_file is None, "raw_file should be None after stop"
    assert test_manager.csv_file is None, "csv_file should be None after stop"
    assert test_manager.raw_csv_file is None, "raw_csv_file should be None after stop"
    
    # Clean up
    client.put("/api/test/finalize")


def test_stop_prevents_data_storage_updates() -> None:
    """Test that data_storage is not updated after stop()."""
    reset_test_state()
    
    payload = {
        "test_id": "test_stop_schema",
        "date": "2026-01-18",
        "operator_name": "Test User",
        "specimen_code": "SCHEMA001",
        "dim_length": 100.0,
        "dim_height": 50.0,
        "dim_width": 25.0,
        "loading_mode": "compression",
        "sensor_spacing": 10.0,
        "ext_support_spacing": 20.0,
        "ext_sensor_spacing": 20.0,
        "load_point_spacing": 15.0
    }
    
    # Prepare and start test
    prep_resp = client.post("/api/test/info", json=payload)
    assert prep_resp.status_code == 204
    
    start_resp = client.put("/api/test/start")
    assert start_resp.status_code == 204
    
    # Collect data for 1 second
    time.sleep(1.0)
    
    # Get initial circular buffer state
    initial_count = test_manager.data_storage.buffers[SensorId.FORCE.value].count
    
    # Stop test
    stop_resp = client.put("/api/test/stop")
    assert stop_resp.status_code == 204
    
    # Verify is_running is now False
    assert not test_manager.is_running, "Test should not be running"
    assert test_manager.is_stopped, "Test should be stopped"
    
    # Manually emit processed data (after stop)
    fake_frame = {
        "timestamp": time.time(),
        "values": {
            SensorId.FORCE.value: 42.0,
            SensorId.DISP_1.value: 1.5,
            SensorId.DISP_2.value: 1.6,
            SensorId.DISP_3.value: 1.7,
            SensorId.DISP_4.value: 1.55,
            SensorId.DISP_5.value: 1.45,
            SensorId.ARC.value: 1.6,
        }
    }
    
    # Trigger the callback (should do nothing because is_running=False)
    test_manager._on_processed_data("processed_data", fake_frame)
    
    # Final count should be the same
    final_count = test_manager.data_storage.buffers[SensorId.FORCE.value].count
    assert final_count == initial_count, \
        f"Circular buffer was updated after stop: {initial_count} → {final_count}"
    
    # Clean up
    client.put("/api/test/finalize")
