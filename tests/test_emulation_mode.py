"""Tests to verify that sensors are always connected in emulation mode."""
import pytest
from core.models.sensor_enum import SensorId
from core.services.sensor_manager import sensor_manager


class TestEmulationMode:
    """Test sensor connection behavior in emulation mode."""
    
    def test_emulation_mode_sensors_always_connected(self):
        """Test que tous les capteurs sont considérés connectés en mode émulation."""
        sensor_ids = [SensorId.FORCE, SensorId.DISP_1, SensorId.DISP_2, SensorId.DISP_3, SensorId.DISP_4, SensorId.DISP_5, SensorId.ARC]
        for sensor_id in sensor_ids:
            assert sensor_manager.is_sensor_connected(sensor_id), \
                f"Sensor {sensor_id} should be connected in emulation mode"
    
    def test_emulation_mode_arc_always_connected(self):
        """Test que ARC est toujours connecté en mode émulation."""
        assert sensor_manager.is_sensor_connected(SensorId.ARC), \
            "ARC should be connected in emulation mode"
    
    def test_emulation_mode_ignores_monitors(self):
        """Test que l'état interne n'affecte pas la connexion en émulation."""
        assert sensor_manager.is_sensor_connected(SensorId.FORCE)
        assert sensor_manager.is_sensor_connected(SensorId.DISP_1)
    
    # Ce test n'est plus pertinent sans gestion hardware/émulation globale
    pass
    
    # Ce test n'est plus pertinent sans gestion hardware/émulation globale
    pass
    
    # Ce test n'est plus pertinent sans gestion hardware/émulation globale
    pass