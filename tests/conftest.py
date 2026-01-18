"""Pytest configuration and fixtures for test suite."""

import pytest
from core.sensor_reconnection import sensor_reconnection_manager, SensorState
from core.services.test_manager import test_manager
import time


@pytest.fixture(autouse=True)
def ensure_sensors_initialized():
    """Ensure all sensors are initialized and connected before each test.
    
    In emulation mode (default), all sensors are always considered connected.
    This fixture ensures tests that need to manipulate connection state can do so.
    """
    # Reset test_manager state at the start of each test
    if test_manager.is_running:
        test_manager.stop_test()
    if test_manager.is_stopped:
        test_manager.finalize_test()
    
    # List of sensors that should be monitored
    sensor_names = ["FORCE", "DISP_1", "DISP_2", "DISP_3", "DISP_4", "DISP_5"]
    
    # Set emulation mode to True by default for most tests
    # Tests that specifically test hardware mode can override this
    sensor_reconnection_manager.emulation_mode = True
    
    for sensor_name in sensor_names:
        if sensor_name not in sensor_reconnection_manager.monitors:
            # Add sensor as connected
            sensor_reconnection_manager.add_sensor(sensor_name, max_silence_time=5.0, is_connected=True)
        else:
            # Ensure it's marked as CONNECTED
            monitor = sensor_reconnection_manager.monitors[sensor_name]
            monitor.state = SensorState.CONNECTED
            monitor.last_data_time = time.time()
            monitor.reconnect_attempts = 0
            monitor.current_backoff_delay = monitor.initial_reconnect_delay
    
    yield
    
    # Reset emulation mode to True after test (in case a test changed it)
    sensor_reconnection_manager.emulation_mode = True
    
    # Clean up test state after each test
    if test_manager.is_running:
        test_manager.stop_test()
    if test_manager.is_stopped:
        test_manager.finalize_test()


@pytest.fixture
def hardware_mode():
    """Fixture to set hardware mode for tests that test actual disconnection behavior."""
    # Save current state
    original_emulation = sensor_reconnection_manager.emulation_mode
    
    # Set to hardware mode
    sensor_reconnection_manager.emulation_mode = False
    
    yield
    
    # Restore original state
    sensor_reconnection_manager.emulation_mode = original_emulation

