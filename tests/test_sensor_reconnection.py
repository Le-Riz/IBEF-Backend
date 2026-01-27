import pytest
import asyncio
import time
from core.models.sensor_enum import SensorId
from core.sensor_reconnection import SensorState
from core.sensor_reconnection import SensorHealthMonitor



class TestSensorHealthMonitor:
    """Test individual sensor health monitoring."""
    
    def test_monitor_initialization(self):
        """Test health monitor initializes correctly."""
        monitor = SensorHealthMonitor(SensorId.FORCE, max_silence_time=5.0)
        assert monitor.sensor_id == SensorId.FORCE
        assert monitor.state == SensorState.CONNECTED
        assert monitor.reconnect_attempts == 0
    
    def test_record_data_resets_state(self):
        """Test recording data resets disconnected state."""
        monitor = SensorHealthMonitor(SensorId.DISP_1)
        monitor.mark_disconnected()
        assert monitor.state == SensorState.DISCONNECTED
        
        monitor.record_data()
        assert monitor.state == SensorState.CONNECTED
    
    def test_check_silence_detects_timeout(self):
        """Test silence detection."""
        monitor = SensorHealthMonitor(SensorId.FORCE, max_silence_time=0.1)
        # Just created, should not be silent
        assert monitor.check_silence() == False
        
        # Wait longer than max_silence_time
        time.sleep(0.2)
        assert monitor.check_silence() == True
    
    def test_backoff_delay_increases(self):
        """Test backoff delay increases exponentially."""
        monitor = SensorHealthMonitor(
            sensor_id=SensorId.DISP_1,
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
            sensor_id=SensorId.FORCE,
            initial_reconnect_delay=1.0,
            max_reconnect_delay=5.0,
            backoff_multiplier=2.0
        )
        
        # Keep getting delays until we hit the cap
        for _ in range(10):
            monitor.get_next_retry_delay()
        
        assert monitor.current_backoff_delay <= 5.0



