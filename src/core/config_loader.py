import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from core.models.sensor_enum import SensorId
from core.models.config_data import configData, configSensorData

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
                json_data = json.load(f)
                # Parse JSON into configData structure
                for sensor_key, sensor_cfg in json_data.get("sensors", {}).items():
                    sensor_id = SensorId[sensor_key]
                    self._config.sensors[sensor_id] = configSensorData(
                        baud=sensor_cfg.get("baud", 9600),
                        description=sensor_cfg.get("description", ""),
                        displayName=sensor_cfg.get("displayName", ""),
                        senderId=sensor_cfg.get("senderId", ""),
                        max=sensor_cfg.get("max", 0.0),
                        enabled=sensor_cfg.get("enabled", True)
                    )
                self._config.emulation = json_data.get("emulation", True)
            logger.info(f"Configuration loaded from {config_path}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse configuration file: {e}")
            self._config = self._get_default_config()
            
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            self._config = self._get_default_config()
    
    @staticmethod
    def _get_default_config() -> configData:
        """Return default configuration."""
        
        return configData(
            emulation=True,
            sensors={
                SensorId.FORCE: configSensorData(baud=115200, description="", displayName="", senderId="", max=0.0, enabled=True),
                SensorId.DISP_1: configSensorData(baud=9600, description="", displayName="", senderId="", max=0.0, enabled=True),
                SensorId.DISP_2: configSensorData(baud=9600, description="", displayName="", senderId="", max=0.0, enabled=False),
                SensorId.DISP_3: configSensorData(baud=9600, description="", displayName="", senderId="", max=0.0, enabled=False),
                SensorId.DISP_4: configSensorData(baud=9600, description="", displayName="", senderId="", max=0.0, enabled=False),
                SensorId.DISP_5: configSensorData(baud=9600, description="", displayName="", senderId="", max=0.0, enabled=False),
            }
        )
    
    def get_emulation_mode(self) -> bool:
        """Get the emulation mode setting."""
        return self._config.emulation
    
    def get_sensor_config(self, sensor_id: SensorId) -> configSensorData:
        """Get configuration for a specific sensor."""
        return self._config.sensors[sensor_id]
    
    def get_sensor_baud(self, sensor_id: SensorId) -> int:
        """Get the baud rate for a specific sensor."""
        sensor_config = self.get_sensor_config(sensor_id)
        if sensor_config:
            return sensor_config.baud
        return 9600
    
    def is_sensor_enabled(self, sensor_id: SensorId) -> bool:
        """
        Check if a sensor is enabled in configuration (enabled: true, except ARC).
        """
        cfg = self.get_sensor_config(sensor_id)
        if cfg is None:
            return False
        # ARC is always enabled (computed sensor)
        if sensor_id == SensorId.ARC:
            return True
        # For real sensors, check 'enabled' field (default True if missing for retrocompatibility)
        return cfg.enabled is True
    
    def get_all_sensors(self) -> Dict[SensorId, configSensorData]:
        """Get all sensor configurations."""
        return self._config.sensors
    
    def get_enabled_sensors(self) -> Dict[SensorId, configSensorData]:
        """Get only sensors that represent real hardware (have a baud)."""
        all_sensors = self.get_all_sensors()
        for sensor in list(all_sensors.keys()):
            if sensor != SensorId.ARC and all_sensors[sensor].enabled is not True:
                all_sensors.pop(sensor)
        return all_sensors
    
    def reload_config(self):
        """Reload configuration from file."""
        self.load_config()
        logger.info("Configuration reloaded")


# Global singleton instance
config_loader = ConfigLoader()
