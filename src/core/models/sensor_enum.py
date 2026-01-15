"""Sensor ID enumeration for type-safe sensor references."""
from enum import Enum


class SensorId(Enum):
    """Enumeration of all available sensors."""
    FORCE = 0
    DISP_1 = 1
    DISP_2 = 2
    DISP_3 = 3
    ARC = 4
