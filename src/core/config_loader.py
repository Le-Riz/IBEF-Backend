import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Loads and manages sensor configuration from JSON file."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._config = {}
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._config = self._get_default_config()
            self.load_config()
            self._initialized = True
    
    @staticmethod
    def get_config_path() -> Path:
        """Get the path to the sensors_config.json file."""
        # Config file should be in the project root/config directory
        config_path = Path(__file__).parent.parent.parent / "config" / "sensors_config.json"
        return config_path
    
    def load_config(self):
        """Load configuration from JSON file."""
        config_path = self.get_config_path()
        
        # Start from defaults to ensure _config is always a dict
        self._config = self._get_default_config()
        
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return
        
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            logger.info(f"Configuration loaded from {config_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse configuration file: {e}")
            self._config = self._get_default_config()
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            self._config = self._get_default_config()
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "emulation": True,
            "sensors": {
                "FORCE": {"baud": 115200, "port": "/dev/ttyUSB0", "enabled": True},
                "DISP_1": {"baud": 9600, "port": "/dev/ttyUSB1", "enabled": True},
                "DISP_2": {"baud": 9600, "port": "/dev/ttyUSB2", "enabled": False},
                "DISP_3": {"baud": 9600, "port": "/dev/ttyUSB3", "enabled": False},
                "DISP_4": {"baud": 9600, "port": "/dev/ttyUSB4", "enabled": False},
                "DISP_5": {"baud": 9600, "port": "/dev/ttyUSB5", "enabled": False},
            }
        }
    
    def get_emulation_mode(self) -> bool:
        """Get the emulation mode setting."""
        return self._config.get("emulation", True)
    
    def get_sensor_config(self, sensor_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific sensor."""
        return self._config.get("sensors", {}).get(sensor_name)
    
    def get_sensor_baud(self, sensor_name: str) -> int:
        """Get the baud rate for a specific sensor."""
        sensor_config = self.get_sensor_config(sensor_name)
        if sensor_config:
            return sensor_config.get("baud", 9600)
        return 9600
    
    def get_sensor_port(self, sensor_name: str) -> Optional[str]:
        """
        Get the port for a specific sensor from auto-detection results.
        Note: Ports are not stored in config file; use port_detector instead.
        """
        return None  # Ports are auto-detected, not in config
    
    def is_sensor_enabled(self, sensor_name: str) -> bool:
        """
        Check if a sensor is in configuration.
        Note: All configured sensors are considered enabled.
        """
        return self.get_sensor_config(sensor_name) is not None
    
    def get_all_sensors(self) -> Dict[str, Dict[str, Any]]:
        """Get all sensor configurations."""
        return self._config.get("sensors", {})
    
    def get_enabled_sensors(self) -> Dict[str, Dict[str, Any]]:
        """Get all sensors (all sensors in config are considered enabled)."""
        return self.get_all_sensors()
    
    def reload_config(self):
        """Reload configuration from file."""
        self.load_config()
        logger.info("Configuration reloaded")


# Global singleton instance
config_loader = ConfigLoader()
