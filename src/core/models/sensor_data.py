"""
Sensor data model.
"""

from dataclasses import dataclass
from core.models.sensor_enum import SensorId

@dataclass
class SensorData:
    """
    Data class representing a single sensor reading.
    """
    timestamp: float
    sensor_id: SensorId
    value: float
    raw_value: float = 0.0
