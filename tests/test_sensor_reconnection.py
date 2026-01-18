import pytest
import asyncio
import time
from core.sensor_reconnection import (
    SensorHealthMonitor, 
    SensorReconnectionManager,
    SensorState,
    sensor_reconnection_manager
)


class TestSensorHealthMonitor:
    """Test individual sensor health monitoring."""
    
    def test_monitor_initialization(self):
        """Test health monitor initializes correctly."""
        monitor = SensorHealthMonitor(sensor_name="FORCE", max_silence_time=5.0)
        assert monitor.sensor_name == "FORCE"
        assert monitor.state == SensorState.CONNECTED
        assert monitor.reconnect_attempts == 0
    
    def test_record_data_resets_state(self):
        """Test recording data resets disconnected state."""
        monitor = SensorHealthMonitor(sensor_name="DISP_1")
        monitor.mark_disconnected()
        assert monitor.state == SensorState.DISCONNECTED
        
        monitor.record_data()
        assert monitor.state == SensorState.CONNECTED
    
    def test_check_silence_detects_timeout(self):
        """Test silence detection."""
        monitor = SensorHealthMonitor(sensor_name="FORCE", max_silence_time=0.1)
        # Just created, should not be silent
        assert monitor.check_silence() == False
        
        # Wait longer than max_silence_time
        time.sleep(0.2)
        assert monitor.check_silence() == True
    
    def test_backoff_delay_increases(self):
        """Test backoff delay increases exponentially."""
        monitor = SensorHealthMonitor(
            sensor_name="DISP_1",
            initial_reconnect_delay=1.0,
            backoff_multiplier=2.0
        )
        
        delay1 = monitor.get_next_retry_delay()
        assert delay1 == 1.0
        assert monitor.current_backoff_delay == 2.0
        
        delay2 = monitor.get_next_retry_delay()
        assert delay2 == 2.0
        assert monitor.current_backoff_delay == 4.0
    
    def test_backoff_delay_caps_at_max(self):
        """Test backoff delay doesn't exceed maximum."""
        monitor = SensorHealthMonitor(
            sensor_name="FORCE",
            initial_reconnect_delay=1.0,
            max_reconnect_delay=5.0,
            backoff_multiplier=2.0
        )
        
        # Keep getting delays until we hit the cap
        for _ in range(10):
            monitor.get_next_retry_delay()
        
        assert monitor.current_backoff_delay <= 5.0


class TestSensorReconnectionManager:
    """Test sensor reconnection manager."""
    
    def test_singleton_pattern(self):
        """Test manager is singleton."""
        mgr1 = SensorReconnectionManager()
        mgr2 = SensorReconnectionManager()
        assert mgr1 is mgr2
    
    def test_add_sensor(self):
        """Test adding sensors to monitor."""
        mgr = SensorReconnectionManager()
        mgr.add_sensor("TEST_FORCE", max_silence_time=5.0)
        
        assert "TEST_FORCE" in mgr.monitors
        assert mgr.monitors["TEST_FORCE"].sensor_name == "TEST_FORCE"
    
    def test_record_sensor_data(self):
        """Test recording data for a sensor."""
        mgr = SensorReconnectionManager()
        mgr.add_sensor("TEST_DISP", max_silence_time=5.0)
        
        monitor = mgr.monitors["TEST_DISP"]
        old_time = monitor.last_data_time
        time.sleep(0.1)
        
        mgr.record_sensor_data("TEST_DISP")
        
        assert monitor.last_data_time > old_time
    
    def test_get_sensor_status(self):
        """Test getting sensor status."""
        mgr = SensorReconnectionManager()
        mgr.add_sensor("TEST_SENSOR", max_silence_time=5.0)
        
        status = mgr.get_sensor_status("TEST_SENSOR")
        assert status is not None
        assert status["name"] == "TEST_SENSOR"
        assert status["state"] == SensorState.CONNECTED.value
        assert "silence_duration" in status
        assert "reconnect_attempts" in status
    
    def test_get_all_statuses(self):
        """Test getting status of all sensors."""
        mgr = SensorReconnectionManager()
        mgr.add_sensor("SENSOR_1")
        mgr.add_sensor("SENSOR_2")
        
        statuses = mgr.get_all_statuses()
        assert len(statuses) >= 2
        assert "SENSOR_1" in statuses
        assert "SENSOR_2" in statuses
    
    def test_register_callback(self):
        """Test registering reconnection callback."""
        mgr = SensorReconnectionManager()
        
        async def dummy_callback(sensor_name: str) -> bool:
            return True
        
        mgr.register_reconnection_callback("TEST", dummy_callback)
        assert "TEST" in mgr.reconnection_callbacks


class TestReconnectionFlow:
    """Test complete reconnection flow."""
    
    @pytest.mark.asyncio
    async def test_silence_detection_triggers_disconnect(self):
        """Test that prolonged silence triggers disconnect."""
        mgr = SensorReconnectionManager()
        mgr.add_sensor("TEST_SENSOR", max_silence_time=0.2)
        
        # Initially connected
        monitor = mgr.monitors["TEST_SENSOR"]
        assert monitor.state == SensorState.CONNECTED
        
        # Wait for silence to be detected
        await asyncio.sleep(0.3)
        
        # Manually trigger the monitor tick
        await mgr._monitor_tick()
        
        # Should be disconnected now
        assert monitor.state == SensorState.DISCONNECTED

