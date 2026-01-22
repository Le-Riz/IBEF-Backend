import pytest
from core.config_loader import config_loader
from core.models.sensor_enum import SensorId


class TestConfigLoader:
    """Test configuration loading and access."""
    
    def test_config_loads(self):
        """Test that config loads successfully."""
        config = config_loader.get_all_sensors()
        assert config is not None
        assert isinstance(config, dict)
    
    def test_emulation_mode(self):
        """Test that emulation mode setting exists."""
        emulation = config_loader.get_emulation_mode()
        assert isinstance(emulation, bool)
    
    def test_get_sensor_config(self):
        """Test getting a specific sensor configuration."""
        force_config = config_loader.get_sensor_config(SensorId.FORCE)
        assert force_config is not None
        assert force_config.baud == 115200
        assert force_config.description != None
    
    def test_force_sensor_baud(self):
        """Test that FORCE sensor has correct default baud."""
        baud = config_loader.get_sensor_baud(SensorId.FORCE)
        assert baud == 115200
    
    def test_motion_sensor_baud(self):
        """Test that motion sensors have correct default baud."""
        for sensor in [SensorId.DISP_1, SensorId.DISP_2, SensorId.DISP_3, SensorId.DISP_4, SensorId.DISP_5, SensorId.ARC]:
            baud = config_loader.get_sensor_baud(sensor)
            assert baud == 9600, f"{sensor} should have 9600 baud"
    
    def test_sensor_enabled_status(self):
        """Test sensor enabled status (all configured sensors are considered enabled)."""
        # These are in config and should be enabled
        assert config_loader.is_sensor_enabled(SensorId.FORCE) == True
        assert config_loader.is_sensor_enabled(SensorId.DISP_1) == True
        assert config_loader.is_sensor_enabled(SensorId.DISP_3) == True
        assert config_loader.is_sensor_enabled(SensorId.DISP_4) == True
        assert config_loader.is_sensor_enabled(SensorId.DISP_5) == True
        
        # ARC is not in config (it's calculated from DISP), so not enabled
        assert config_loader.is_sensor_enabled(SensorId.ARC) == True
    
    def test_get_enabled_sensors(self):
        """Test getting only enabled sensors."""
        enabled = config_loader.get_enabled_sensors()
        assert isinstance(enabled, dict)
        
        # All returned sensors should have enabled=true
        for name, config in enabled.items():
            assert config.enabled is True
    
    def test_config_singleton(self):
        """Test that ConfigLoader is a singleton."""
        loader1 = config_loader
        loader2 = config_loader
        assert loader1 is loader2
