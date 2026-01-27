from dataclasses import dataclass, field
from typing import Dict

from core.models.sensor_enum import SensorId


@dataclass
class defaultConfigSensorData:
    id: SensorId
    description : str = "No description"
    displayName : str = "Unnamed Sensor"
    max: float = 5.0

@dataclass
class configSensorData(defaultConfigSensorData):
    baud : int = 115200
    serialId : str = ""
    enabled: bool = True

@dataclass
class calculatedConfigSensorData(defaultConfigSensorData):
    dependencies: list[configSensorData] = field(default_factory=list[configSensorData])

@dataclass
class configData:
    sensors : Dict[SensorId, defaultConfigSensorData]
    emulation : bool = True