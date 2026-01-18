import serial
import serial.tools.list_ports
import threading
import time
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DetectedSensor:
    """Represents a detected sensor on a serial port."""
    sensor_name: str  # e.g., "FORCE", "DISP_1"
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
        self._detection_lock = threading.Lock()
    
    @staticmethod
    def get_available_ports() -> List[str]:
        """Get list of available serial ports."""
        ports = []
        for port_info in serial.tools.list_ports.comports():
            ports.append(port_info.device)
        return ports
    
    def probe_sensor(self, port: str, baud: int, timeout: float = 1.0) -> Optional[str]:
        """
        Probe a single port at a given baud rate to identify the sensor type.
        
        Returns:
            Sensor name (FORCE, DISP_1, etc.) or None if unrecognized
        """
        try:
            ser = serial.Serial(port, baud, timeout=timeout)
            time.sleep(0.5)  # Wait for connection to stabilize
            
            sensor_detected = None
            for _ in range(10):  # Try to read up to 10 lines
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8').strip()
                        if line:
                            sensor_detected = self._identify_sensor_from_line(line)
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
    def _identify_sensor_from_line(line: str) -> Optional[str]:
        """
        Identify sensor type from a single line of serial data.
        
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
            return "DISP"  # Generic DISP (will be numbered based on order)
        
        return None
    
    def auto_detect_sensors(self, sensor_bauds: Dict[str, int]) -> Dict[str, DetectedSensor]:
        """
        Automatically detect all sensors connected to the system.
        
        Args:
            sensor_bauds: Mapping of sensor name to expected baud rate
                         e.g., {"FORCE": 115200, "DISP_1": 9600, ...}
        
        Returns:
            Dictionary mapping sensor_name to DetectedSensor
        """
        logger.info("Starting automatic sensor detection...")
        available_ports = self.get_available_ports()
        logger.info(f"Found {len(available_ports)} available ports: {available_ports}")
        
        detected = {}
        used_ports = set()
        disp_count = 0  # Counter for DISP sensors found
        
        # First pass: try each port with each sensor's expected baud
        for port in available_ports:
            for sensor_name, baud in sensor_bauds.items():
                if port in used_ports:
                    continue
                
                # Skip DISP sensors we've already found enough of
                if sensor_name.startswith("DISP") and disp_count >= 3:
                    continue
                
                sensor_type = self.probe_sensor(port, baud)
                
                if sensor_type == "FORCE" and sensor_name == "FORCE":
                    detected[sensor_name] = DetectedSensor(
                        sensor_name=sensor_name,
                        port=port,
                        baud=baud,
                        confidence=0.95
                    )
                    used_ports.add(port)
                    logger.info(f"✓ Detected {sensor_name} on {port} @ {baud} baud")
                    break
                
                elif sensor_type == "DISP" and sensor_name.startswith("DISP"):
                    detected[sensor_name] = DetectedSensor(
                        sensor_name=sensor_name,
                        port=port,
                        baud=baud,
                        confidence=0.90
                    )
                    used_ports.add(port)
                    disp_count += 1
                    logger.info(f"✓ Detected {sensor_name} on {port} @ {baud} baud")
                    break
        
        # Second pass: try alternative bauds for undetected ports
        if len(detected) < len(sensor_bauds):
            alternative_bauds = [4800, 9600, 19200, 38400, 57600, 115200]
            
            for port in available_ports:
                if port in used_ports:
                    continue
                
                logger.info(f"Port {port} undetected with standard bauds, trying alternatives...")
                
                for alt_baud in alternative_bauds:
                    sensor_type = self.probe_sensor(port, alt_baud)
                    
                    if sensor_type == "FORCE" and "FORCE" not in detected:
                        detected["FORCE"] = DetectedSensor(
                            sensor_name="FORCE",
                            port=port,
                            baud=alt_baud,
                            confidence=0.7  # Lower confidence for alternative baud
                        )
                        used_ports.add(port)
                        logger.warning(f"⚠ Detected FORCE on {port} @ {alt_baud} baud (expected 115200)")
                        break
                    
                    elif sensor_type == "DISP" and disp_count < 3:
                        disp_num = disp_count + 1
                        disp_name = f"DISP_{disp_num}"
                        detected[disp_name] = DetectedSensor(
                            sensor_name=disp_name,
                            port=port,
                            baud=alt_baud,
                            confidence=0.7
                        )
                        used_ports.add(port)
                        disp_count += 1
                        logger.warning(f"⚠ Detected {disp_name} on {port} @ {alt_baud} baud (expected 9600)")
                        break
        
        # Store results
        self.detected_sensors = detected
        self.port_to_sensor = {s.port: s.sensor_name for s in detected.values()}
        
        logger.info(f"Sensor detection complete. Found {len(detected)} sensors:")
        for sensor_name, sensor in detected.items():
            logger.info(f"  - {sensor_name}: {sensor.port} @ {sensor.baud} baud (confidence: {sensor.confidence:.0%})")
        
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
