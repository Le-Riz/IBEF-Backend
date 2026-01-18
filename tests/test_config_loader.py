import pytest
from core.config_loader import config_loader


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
        force_config = config_loader.get_sensor_config("FORCE")
        assert force_config is not None
        assert "baud" in force_config
        assert "description" in force_config
    
    def test_force_sensor_baud(self):
        """Test that FORCE sensor has correct default baud."""
        baud = config_loader.get_sensor_baud("FORCE")
        assert baud == 115200
    
    def test_motion_sensor_baud(self):
        """Test that motion sensors have correct default baud."""
        for sensor in ["DISP_1", "DISP_2", "DISP_3", "DISP_4", "DISP_5", "ARC"]:
            baud = config_loader.get_sensor_baud(sensor)
            assert baud == 9600, f"{sensor} should have 9600 baud"
    
    def test_sensor_enabled_status(self):
        """Test sensor enabled status (all configured sensors are considered enabled)."""
        # These are in config and should be enabled
        assert config_loader.is_sensor_enabled("FORCE") == True
        assert config_loader.is_sensor_enabled("DISP_1") == True
        assert config_loader.is_sensor_enabled("DISP_3") == True
        assert config_loader.is_sensor_enabled("DISP_4") == True
        assert config_loader.is_sensor_enabled("DISP_5") == True
        
        # ARC is not in config (it's calculated from DISP), so not enabled
        assert config_loader.is_sensor_enabled("ARC") == False
    
    def test_get_port(self):
        """Test getting sensor port from config (should return None as ports are auto-detected)."""
        port = config_loader.get_sensor_port("FORCE")
        # Ports are not stored in config, they are auto-detected by port_detector
        assert port is None
    
    def test_get_enabled_sensors(self):
        """Test getting only enabled sensors."""
        enabled = config_loader.get_enabled_sensors()
        assert isinstance(enabled, dict)
        
        # All returned sensors should have enabled=true
        for name, config in enabled.items():
            assert config.get("enabled", True) == True
    
    def test_invalid_sensor(self):
        """Test handling of invalid sensor name."""
        config = config_loader.get_sensor_config("NONEXISTENT")
        assert config is None
    
    def test_config_singleton(self):
        """Test that ConfigLoader is a singleton."""
        loader1 = config_loader
        loader2 = config_loader
        assert loader1 is loader2
