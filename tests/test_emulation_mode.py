"""Tests to verify that sensors are always connected in emulation mode."""
import pytest
from core.models.sensor_enum import SensorId
from core.sensor_reconnection import sensor_reconnection_manager, SensorState


class TestEmulationMode:
    """Test sensor connection behavior in emulation mode."""
    
    def test_emulation_mode_sensors_always_connected(self):
        """Test that in emulation mode, all sensors are considered connected."""
        # Ensure we're in emulation mode
        sensor_reconnection_manager.emulation_mode = True
        
        # Test all sensor names
        sensor_ids = [SensorId.FORCE, SensorId.DISP_1, SensorId.DISP_2, SensorId.DISP_3, SensorId.DISP_4, SensorId.DISP_5, SensorId.ARC]
        
        for sensor_id in sensor_ids:
            assert sensor_reconnection_manager.is_sensor_connected(sensor_id), \
                f"Sensor {sensor_id} should be connected in emulation mode"
    
    def test_emulation_mode_arc_always_connected(self):
        """Test that ARC is connected in emulation mode regardless of other sensors."""
        sensor_reconnection_manager.emulation_mode = True
        
        # Even though DISP_2 and DISP_3 aren't in monitors, they should be considered connected
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.ARC), \
            "ARC should be connected in emulation mode"
    
    def test_emulation_mode_ignores_monitors(self):
        """Test that emulation mode ignores the monitors dictionary."""
        sensor_reconnection_manager.emulation_mode = True
        
        # Clear monitors to simulate uninitialized state
        sensor_reconnection_manager.monitors.clear()
        
        # Should still be connected
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.FORCE)
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.DISP_1)
    
    def test_hardware_mode_respects_monitors(self):
        """Test that hardware mode respects the monitors state."""
        sensor_reconnection_manager.emulation_mode = False
        
        # Clear monitors - sensors should not be connected
        sensor_reconnection_manager.monitors.clear()
        
        assert not sensor_reconnection_manager.is_sensor_connected(SensorId.FORCE)
        assert not sensor_reconnection_manager.is_sensor_connected(SensorId.DISP_1)
    
    def test_hardware_mode_arc_requires_dependencies(self):
        """Test that in hardware mode, ARC requires all dependencies connected."""
        sensor_reconnection_manager.emulation_mode = False
        sensor_reconnection_manager.monitors.clear()
        
        # Add DISP_1 but not DISP_2 and DISP_3
        sensor_reconnection_manager.add_sensor(SensorId.DISP_1, is_connected=True)
        
        # ARC should not be connected because DISP_2 and DISP_3 are missing
        assert not sensor_reconnection_manager.is_sensor_connected(SensorId.ARC)
    
    def test_emulation_mode_stays_true_through_workflow(self):
        """Test that emulation mode persists as expected."""
        # Set to emulation
        sensor_reconnection_manager.emulation_mode = True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.FORCE)
        
        # Set to hardware
        sensor_reconnection_manager.emulation_mode = False
        sensor_reconnection_manager.monitors.clear()
        assert not sensor_reconnection_manager.is_sensor_connected(SensorId.FORCE)
        
        # Back to emulation
        sensor_reconnection_manager.emulation_mode = True
        assert sensor_reconnection_manager.is_sensor_connected(SensorId.FORCE)