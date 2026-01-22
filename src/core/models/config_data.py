from dataclasses import dataclass
from typing import Dict

from core.models.sensor_enum import SensorId


@dataclass
class configSensorData:
    baud : int = 9600
    description : str = ""
    displayName : str = ""
    senderId : str = ""
    max: float = 5.0
    enabled: bool = True

@dataclass
class configData:
    sensors : Dict[SensorId, configSensorData]
    emulation : bool = True