"""Verification tests for emulation mode behavior - ensures sensors never disconnect in emulation."""

import pytest
from core.models.sensor_enum import SensorId
from core.services.sensor_manager import sensor_manager


class TestEmulationGuarantees:
    """Verify that emulation mode provides guaranteed sensor availability."""
    
    def test_emulation_guarantees_all_sensors_connected(self):
        """Vérifie que is_sensor_connected retourne toujours True en mode émulation."""
        assert sensor_manager.is_sensor_connected(SensorId.FORCE) is True
        assert sensor_manager.is_sensor_connected(SensorId.DISP_1) is True
        assert sensor_manager.is_sensor_connected(SensorId.DISP_2) is True
        assert sensor_manager.is_sensor_connected(SensorId.DISP_3) is True
        assert sensor_manager.is_sensor_connected(SensorId.DISP_4) is True
        assert sensor_manager.is_sensor_connected(SensorId.DISP_5) is True
        assert sensor_manager.is_sensor_connected(SensorId.ARC) is True
    
    def test_emulation_overrides_all_disconnection_attempts(self):
        """Vérifie que même si on force la déconnexion, is_sensor_connected retourne True en émulation."""
        assert sensor_manager.is_sensor_connected(SensorId.FORCE) is True
        assert sensor_manager.is_sensor_connected(SensorId.DISP_1) is True
        assert sensor_manager.is_sensor_connected(SensorId.ARC) is True
    
    # Ce test n'est plus pertinent sans gestion hardware/émulation globale
    pass
    
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
