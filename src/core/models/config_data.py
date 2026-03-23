"""Configuration data models for sensors and application settings.

This module defines dataclasses for storing sensor configuration, including
default settings, serial communication parameters, calculated dependencies,
and global application configuration.
"""

from dataclasses import dataclass, field
from typing import Dict

from core.models.sensor_enum import SensorId


@dataclass
class defaultConfigSensorData:
    """Base sensor configuration with default values.
    
    Attributes:
        id: Unique sensor identifier from SensorId enum.
        description: Human-readable description of the sensor.
        displayName: Name to display in user interfaces.
        max: Maximum measurement value for the sensor.
    """
    id: SensorId
    description : str = "No description"
    displayName : str = "Unnamed Sensor"
    max: float = 5.0

@dataclass
class configSensorData(defaultConfigSensorData):
    """Sensor configuration with serial communication parameters.
    
    Extends defaultConfigSensorData with physical serial connection details.
    
    Attributes:
        baud: Serial port baud rate (default: 115200).
        serialId: Serial port identifier/device path.
        enabled: Whether this sensor is actively monitored.
    """
    baud : int = 115200
    serialId : str = ""
    enabled: bool = True

@dataclass
class calculatedConfigSensorData(defaultConfigSensorData):
    """Configuration for calculated/derived sensors.
    
    Extends defaultConfigSensorData for sensors that compute values based on
    other sensor measurements rather than direct serial input.
    
    Attributes:
        dependencies: List of source sensors required for calculations.
    """
    dependencies: list[configSensorData] = field(default_factory=list[configSensorData])

@dataclass
class configData:
    """Global application configuration.
    
    Attributes:
        sensors: Dictionary mapping sensor IDs to their configuration.
        emulation: List of sensor IDs to run in emulation/simulation mode.
    """
    sensors : Dict[SensorId, defaultConfigSensorData]
    emulation : list[SensorId] = field(default_factory=list)