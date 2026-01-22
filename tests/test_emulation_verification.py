"""Verification tests for emulation mode behavior - ensures sensors never disconnect in emulation."""

import pytest
from core.models.sensor_enum import SensorId
from core.sensor_reconnection import sensor_reconnection_manager, SensorState


class TestEmulationGuarantees:
    """Verify that emulation mode provides guaranteed sensor availability."""
    
    def test_emulation_guarantees_all_sensors_connected(self):
        """Verify the core guarantee: in emulation, is_sensor_connected always returns True."""
        sensor_reconnection_manager.emulation_mode = True
        
        # Even if monitor is empty, should return True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.FORCE) is True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.DISP_1) is True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.DISP_2) is True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.DISP_3) is True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.DISP_4) is True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.DISP_5) is True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.ARC) is True
        
        # Reset emulation mode
        sensor_reconnection_manager.emulation_mode = True
    
    def test_emulation_overrides_all_disconnection_attempts(self):
        """Verify that emulation mode overrides any disconnection state."""
        sensor_reconnection_manager.emulation_mode = True
        
        # Manually mark sensors as disconnected
        for sensor_id in [SensorId.FORCE, SensorId.DISP_1, SensorId.DISP_2, SensorId.DISP_3, SensorId.DISP_4, SensorId.DISP_5]:
            if sensor_id in sensor_reconnection_manager.monitors:
                sensor_reconnection_manager.monitors[sensor_id].state = SensorState.DISCONNECTED
        
        # Even though we marked them as disconnected, emulation mode should return True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.FORCE) is True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.DISP_1) is True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.ARC) is True
        
        # Reset emulation mode
        sensor_reconnection_manager.emulation_mode = True
    
    def test_hardware_mode_respects_disconnection(self):
        """Verify that hardware mode actually respects disconnection state."""
        sensor_reconnection_manager.emulation_mode = False
        
        # Ensure sensor exists
        if SensorId.FORCE not in sensor_reconnection_manager.monitors:
            sensor_reconnection_manager.add_sensor(SensorId.FORCE, max_silence_time=5.0, is_connected=True)
        
        # Mark as disconnected
        sensor_reconnection_manager.monitors[SensorId.FORCE].state = SensorState.DISCONNECTED
        
        # In hardware mode, should return False
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.FORCE) is False
        
        # Clean up
        sensor_reconnection_manager.emulation_mode = True
    
    def test_emulation_vs_hardware_behavior_difference(self):
        """Verify the critical difference between emulation and hardware modes."""
        # Ensure sensor exists
        if SensorId.DISP_2 not in sensor_reconnection_manager.monitors:
            sensor_reconnection_manager.add_sensor(SensorId.DISP_2, max_silence_time=5.0, is_connected=True)
        
        # Mark as disconnected
        sensor_reconnection_manager.monitors[SensorId.DISP_2].state = SensorState.DISCONNECTED
        
        # In emulation mode: should return True (emulation override)
        sensor_reconnection_manager.emulation_mode = True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.DISP_2) is True
        
        # In hardware mode: should return False (respects disconnection)
        sensor_reconnection_manager.emulation_mode = False
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.DISP_2) is False
        
        # Back to emulation
        sensor_reconnection_manager.emulation_mode = True
