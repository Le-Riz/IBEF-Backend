import serial
import serial.tools.list_ports
import threading
import time
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

from core.models.config_data import configSensorData
from core.models.sensor_enum import SensorId

logger = logging.getLogger(__name__)


@dataclass
class DetectedSensor:
    """Represents a detected sensor on a serial port."""
    sensor_name: SensorId  # e.g., "FORCE", "DISP_1"
    port: str  # e.g., "/dev/ttyUSB0"
    baud: int  # Detected baud rate
    confidence: float  # 0.0-1.0, how confident we are about the detection


class PortDetector:
    """Automatically detects and maps sensors to serial ports."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PortDetector, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.detected_sensors: Dict[str, DetectedSensor] = {}
        self.port_to_sensor: Dict[str, str] = {}  # Maps port to sensor_name
        self.used_ports: set = set()  # Persistent list of ports that have been assigned
        self._detection_lock = threading.Lock()
    
    @staticmethod
    def get_available_ports() -> List[str]:
        """Get list of available serial ports."""
        ports = []
        for port_info in serial.tools.list_ports.comports():
            ports.append(port_info.device)
        return ports
    
    def probe_sensor(self, port: str, baud: int, expected_sender_id: Optional[str] = None, timeout: float = 3.0) -> Optional[str]:
        """
        Probe a single port at a given baud rate to identify the sensor type.
        
        Args:
            port: Serial port to probe
            baud: Baud rate to use
            expected_sender_id: For DISP sensors, validate that the sender_id matches (e.g., "0x2E01")
            timeout: Timeout for reading
        
        Returns:
            Sensor name (FORCE, DISP_1, etc.) or None if unrecognized
        """
        try:
            ser = serial.Serial(port, baud, timeout=timeout)
            time.sleep(1.0)  # Wait for connection to stabilize
            
            sensor_detected = None
            for _ in range(30):  # Try to read up to 30 lines (3 seconds total)
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8').strip()
                        if line:
                            sensor_detected = self._identify_sensor_from_line(line, expected_sender_id)
                            if sensor_detected:
                                break
                    except (UnicodeDecodeError, AttributeError):
                        # Wrong baud rate, data is unreadable
                        pass
                time.sleep(0.1)
            
            ser.close()
            return sensor_detected
            
        except serial.SerialException as e:
            logger.debug(f"Failed to probe {port} at {baud} baud: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected error probing {port}: {e}")
            return None
    
    @staticmethod
    def _identify_sensor_from_line(line: str, expected_sender_id: Optional[str] = None) -> Optional[str]:
        """
        Identify sensor type from a single line of serial data.
        
        Args:
            line: Serial data line
            expected_sender_id: For DISP sensors, validate sender_id matches (e.g., "0x2E01")
        
        Returns:
            Sensor name or None if unrecognized
        """
        # FORCE sensor pattern: "ASC2 ..." with 5 parts containing numbers
        if "ASC2" in line:
            parts = line.split()
            if len(parts) >= 5:
                try:
                    # Try to parse as FORCE format
                    float(parts[4])  # Calibrated value
                    return "FORCE"
                except (ValueError, IndexError):
                    pass
        
        # Motion sensor pattern: "SPC_VAL" with "usSenderId" and "Val="
        if "SPC_VAL" in line and "usSenderId" in line and "Val=" in line:
            # If we're looking for a specific sender_id, validate it
            if expected_sender_id:
                try:
                    # Extract sender_id from line
                    for part in line.split():
                        if part.startswith("usSenderId="):
                            actual_sender_id = part.split("=")[1]
                            if actual_sender_id == expected_sender_id:
                                return "DISP"
                            else:
                                # Wrong sender_id, not the sensor we're looking for
                                return None
                except (IndexError, ValueError):
                    pass
            else:
                # No specific sender_id expected, just detect as DISP
                return "DISP"
        
        return None
    
    def auto_detect_sensors(self, sensor_bauds: Dict[SensorId, int], sensor_configs: Dict[SensorId, configSensorData], verbose: bool = True) -> Dict[SensorId, DetectedSensor]:
        """
        Automatically detect all sensors connected to the system.
        
        Args:
            sensor_bauds: Mapping of sensor name to expected baud rate
                         e.g., {"FORCE": 115200, "DISP_1": 9600, ...}
            sensor_configs: Optional sensor configurations with sender_id info
            verbose: Whether to log info/warning messages (default True)
        
        Returns:
            Dictionary mapping sensor_name to DetectedSensor (only those physically connected)
        """
        if verbose:
            logger.info("Starting automatic sensor detection...")
        available_ports = self.get_available_ports()
        if verbose:
            logger.info(f"Found {len(available_ports)} available ports: {available_ports}")
        
        detected = {}
        local_used_ports = set(self.used_ports)  # Copy persistent used_ports
        disp_count = 0  # Counter for DISP sensors found
        max_disp = max(0, sum(1 for name in sensor_bauds if (
            name == SensorId.DISP_1 or
            name == SensorId.DISP_2 or
            name == SensorId.DISP_3 or
            name == SensorId.DISP_4 or
            name == SensorId.DISP_5
        )))
        
        # Single pass: try each port with each sensor's configured baud only
        for port in available_ports:
            if port in local_used_ports:
                continue
            
            for sensor_id, baud in sensor_bauds.items():
                # Skip DISP sensors we've already found enough of
                if (sensor_id == SensorId.DISP_1 or
                    sensor_id == SensorId.DISP_2 or
                    sensor_id == SensorId.DISP_3 or
                    sensor_id == SensorId.DISP_4 or
                    sensor_id == SensorId.DISP_5) and max_disp and disp_count >= max_disp:
                    continue
                
                # Skip if this sensor is already detected
                if sensor_id in detected:
                    continue
                
                # Get expected sender_id for DISP sensors from config
                expected_sender_id = None
                if (sensor_id == SensorId.DISP_1 or
                    sensor_id == SensorId.DISP_2 or
                    sensor_id == SensorId.DISP_3 or
                    sensor_id == SensorId.DISP_4 or
                    sensor_id == SensorId.DISP_5) and sensor_configs and sensor_id in sensor_configs:
                    expected_sender_id = sensor_configs[sensor_id].senderId
                
                sensor_type = self.probe_sensor(port, baud, expected_sender_id=expected_sender_id)
                
                if sensor_type == "FORCE" and sensor_id == SensorId.FORCE:
                    detected[sensor_id] = DetectedSensor(
                        sensor_name=sensor_id,
                        port=port,
                        baud=baud,
                        confidence=0.95
                    )
                    local_used_ports.add(port)
                    if verbose:
                        logger.info(f"✓ Detected {sensor_id} on {port} @ {baud} baud")
                    break
                
                elif sensor_type == "DISP" and (sensor_id == SensorId.DISP_1 or
                                                  sensor_id == SensorId.DISP_2 or
                                                  sensor_id == SensorId.DISP_3 or
                                                  sensor_id == SensorId.DISP_4 or
                                                  sensor_id == SensorId.DISP_5):
                    detected[sensor_id] = DetectedSensor(
                        sensor_name=sensor_id,
                        port=port,
                        baud=baud,
                        confidence=0.90
                    )
                    local_used_ports.add(port)
                    disp_count += 1
                    if verbose:
                        logger.info(f"✓ Detected {sensor_id} on {port} @ {baud} baud")
                    break
        
        # Update persistent state
        self.detected_sensors = detected
        self.port_to_sensor = {s.port: s.sensor_name for s in detected.values()}
        self.used_ports = local_used_ports  # Save used ports persistently
        
        if verbose:
            logger.info(f"Sensor detection complete. Found {len(detected)} sensors:")
            for sensor_id, sensor in detected.items():
                logger.info(f"  - {sensor_id}: {sensor.port} @ {sensor.baud} baud (confidence: {sensor.confidence:.0%})")
        
        # Warn about missing sensors (only if verbose)
        missing_sensors = set(sensor_bauds.keys()) - set(detected.keys())
        if missing_sensors and verbose:
            missing_list = ", ".join(sorted(sensor.name for sensor in missing_sensors))
            logger.warning(f"The following configured sensors were not detected (they may not be connected): {missing_list}")
        
        return detected
    
    def get_sensor_port(self, sensor_name: str) -> Optional[str]:
        """Get the port for a specific sensor."""
        sensor = self.detected_sensors.get(sensor_name)
        if sensor:
            return sensor.port
        return None
    
    def get_sensor_baud(self, sensor_name: str) -> Optional[int]:
        """Get the baud rate for a specific sensor."""
        sensor = self.detected_sensors.get(sensor_name)
        if sensor:
            return sensor.baud
        return None
    
    def is_sensor_available(self, sensor_name: str) -> bool:
        """Check if a sensor is detected."""
        return sensor_name in self.detected_sensors
    
    def get_all_detected(self) -> Dict[str, DetectedSensor]:
        """Get all detected sensors."""
        return self.detected_sensors.copy()


# Global singleton instance
port_detector = PortDetector()
