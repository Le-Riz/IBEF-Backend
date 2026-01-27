from dataclasses import dataclass, field
from typing import Dict

@dataclass
class defaultConfigSensorData:
    id: int
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
    sensors : Dict[int, defaultConfigSensorData]
    emulation : bool = True

def is_enabled_sensor(sensor: defaultConfigSensorData) -> bool:
    """Check if a sensor is enabled in configuration (enabled: true, except ARC)."""
    if isinstance(sensor, configSensorData):
        
        return sensor.enabled is True
    elif isinstance(sensor, calculatedConfigSensorData):
        for calc_sensor in sensor.dependencies:
            if not is_enabled_sensor(calc_sensor):
                return False
        return True
    return False
    
    
item1 = configSensorData(id=1, baud=115200, description="A sensor", displayName="Sensor 1", serialId="S1", max=100.0, enabled=True)
item2 = configSensorData(id=2, baud=9600, description="Another sensor", displayName="Sensor 2", serialId="S2", max=50.0, enabled=False)
item3 = calculatedConfigSensorData(id=3, description="Calculated sensor", displayName="Calc Sensor", max=200.0, dependencies=[item1, item2])
config = configData(sensors={1: item1, 2: item2, 3: item3}, emulation=False)
print(is_enabled_sensor(config.sensors[1]))
print(is_enabled_sensor(config.sensors[2]))
print(is_enabled_sensor(config.sensors[3]))