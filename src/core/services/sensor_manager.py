import os
import queue
import threading
import time
import logging
import math
import random
from typing import Callable, Dict, Optional

from core.config_loader import config_loader
from core.models.config_data import calculatedConfigSensorData
from core.models.sensor_data import SensorData
from core.models.sensor_enum import SensorId
from core.sensor_reconnection import SensorsTask
from core.services.serial_handler import SerialHandler

logger = logging.getLogger(__name__)
PORT_PREFIX = "/dev/serial/by-id/"

class SensorManager:
    """
    Manages sensor data acquisition from serial ports (via EventHub) or emulation.
    """
    def __init__(self):
        self.running = False
        self.emulation_mode = False
        self.sensors: list[SensorData] = [SensorData(0.0, id, math.nan, math.nan) for id in SensorId]
        self._thread: Optional[threading.Thread] = None
        self.offsets: list[float] = [0.0 for _ in SensorId]
        self._serial_handlers: list[SerialHandler] = []
        self.queue: queue.Queue[tuple[SensorId, str, float]] = queue.Queue(maxsize=1024)
        self._sensors_task: SensorsTask = SensorsTask(self.queue)
        self.notify_funcs: list[Callable[[SensorData], None]] = []
        self.want_zero: bool = False
        self.sensor_ports: list[str] = [""] * len(SensorId)
        arc_config = config_loader.get_sensor_config(SensorId.ARC)
        self.arc_sensor_dependencies: list[SensorId] = []
        if isinstance(arc_config, calculatedConfigSensorData):
            self.arc_sensor_dependencies: list[SensorId] = [dep.id for dep in arc_config.dependencies]

    def start(self, emulation=False, sensor_ports: Optional[Dict[SensorId, tuple[str, int]]] = None):
        """Start sensor data acquisition. If not in emulation, expects sensor_ports: Dict[SensorId, (port, baud)]"""
        if self.running:
            if self.emulation_mode != emulation:
                self.stop()
            else:
                return

        self.emulation_mode = emulation
        self.running = True
        logger.info(f"SensorManager started (Emulation: {emulation})")

        if self.emulation_mode:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        else:
            # Launch a SensorTask for each real sensor
            if sensor_ports is None:
                raise ValueError("sensor_ports must be provided in hardware mode")
            for sensor_id, (port, baud) in sensor_ports.items():
                if port == "":
                    logger.warning(f"Sensor {sensor_id} has no assigned port, skipping...")
                    continue
                self.sensor_ports[sensor_id.value] = port
                full_port = PORT_PREFIX + port
                serial_handler = SerialHandler(sensor_id=sensor_id, port=full_port, queue=self.queue, 
                                               baudrate=baud, serial_timeout=0.5)
                
                serial_handler.start()
                self._serial_handlers.append(serial_handler)
            
            self._sensors_task.start()

    def set_mode(self, emulation: bool):
        """Set the operation mode (emulation or real hardware)."""
        if self.running:
            self.stop()
            self.start(emulation)
        else:
            self.emulation_mode = emulation

    def is_sensor_connected(self, sensor_id: SensorId) -> bool:
        """
        Check if a sensor is currently connected.
        Handles ARC and emulation logic.
        """
        # Emulation mode: enabled in config = connected
        if self.emulation_mode:
            
            return config_loader.is_sensor_enabled(sensor_id)
        
        # Hardware mode: check if we have a running SensorTask
        if sensor_id == SensorId.ARC:
            for sensor in self.arc_sensor_dependencies:
                if not self.is_sensor_connected(sensor):
                    return False
            return True
        
        return os.path.exists(self.sensor_ports[sensor_id.value])
    
    def stop(self):
        """Stop sensor data acquisition."""
        self.running = False
        if self._thread:
            self._thread.join()
            self._thread = None
        # Stop all serial handlers
        for handler in self._serial_handlers:
            handler.stop()
        self._serial_handlers.clear()
        self._sensors_task.stop()
        logger.info("SensorManager stopped")

    def _loop(self):
        start_time = time.time()
        while self.running:
            if self.emulation_mode:
                self._emulate_data(start_time)
            time.sleep(0.1) # Rate limit

    def _on_serial_data(self, sensorId: SensorId, time: float, line: str):
        # Only process if NOT in emulation mode
        if not self.emulation_mode:
            try:
                if sensorId == SensorId.FORCE:
                    self._parse_force(sensorId, time, line)
                    
                elif (sensorId == SensorId.DISP_1 or
                      sensorId == SensorId.DISP_2 or
                      sensorId == SensorId.DISP_3 or
                      sensorId == SensorId.DISP_4 or
                      sensorId == SensorId.DISP_5):
                    self._parse_motion(sensorId, time, line)
                    
            except Exception as e:
                logger.warning(f"Error parsing line: {line} -> {e}")

    def set_zero(self, sensor_id: SensorId):
        """Manually zero a sensor by updating its offset."""
        if sensor_id in SensorId:
            self.want_zero = True

    def _parse_force(self, sensorId: SensorId, time: float, line: str):
        # ASC2 20945595 -165341 -1.527986e-01 -4.965955e+01 -0.000000e+00
        parts = line.split()
        if len(parts) >= 5:
            try:
                val = float(parts[4]) # Calibrated value
                self._notify(sensorId, time, val)
            except ValueError:
                pass

    def _parse_motion(self, sensorId: SensorId, time: float, line: str):
        # 76 144 262 us SPC_VAL usSenderId=0x2E01 ulMicros=76071216 Val=0.000
        parts = line.split()
        sender_id = None
        val = None
        for part in parts:
            if part.startswith("usSenderId="):
                sender_id = part.split("=")[1]
            elif part.startswith("Val="):
                try:
                    val = float(part.split("=")[1])
                except ValueError:
                    pass
        
        if sender_id and val is not None:
            self._notify(sensorId, time, val)

    def _calculate_arc(self, data: SensorData):
        if (data.sensor_id in self.arc_sensor_dependencies):
            if(not math.isnan(self.sensors[SensorId.DISP_1.value].value) and
               not math.isnan(self.sensors[SensorId.DISP_2.value].value) and
               not math.isnan(self.sensors[SensorId.DISP_3.value].value)):
                self.sensors[SensorId.ARC.value].raw_value = self.sensors[SensorId.DISP_1.value].raw_value - (self.sensors[SensorId.DISP_2.value].raw_value + self.sensors[SensorId.DISP_3.value].raw_value) / 2
                self.sensors[SensorId.ARC.value].value = self.sensors[SensorId.DISP_1.value].value - (self.sensors[SensorId.DISP_2.value].value + self.sensors[SensorId.DISP_3.value].value) / 2
                self.sensors[SensorId.ARC.value].offset = self.sensors[SensorId.DISP_1.value].offset - (self.sensors[SensorId.DISP_2.value].offset + self.sensors[SensorId.DISP_3.value].offset) / 2
                self.sensors[SensorId.ARC.value].timestamp = data.timestamp

                return self.sensors[SensorId.ARC.value]
        return None

    def _emulate_data(self, start_time):
        elapsed = time.time() - start_time

        from core.config_loader import config_loader

        # Emulate Force (Sine wave) only if enabled
        if config_loader.is_sensor_enabled(SensorId.FORCE):
            force_val = 500 + 500 * math.sin(elapsed) + random.uniform(-10, 10)
            self._notify(SensorId.FORCE, time.time(), force_val)

        # Emulate Displacement (Linear + Noise) with per-sensor phase offsets to avoid overlap
        phase_offsets = {
            SensorId.DISP_1: 0.0,
            SensorId.DISP_2: 1.5,
            SensorId.DISP_3: 3.0,
            SensorId.DISP_4: 4.5,
            SensorId.DISP_5: 6.0,
        }

        for sensor_id, phase in phase_offsets.items():
            if config_loader.is_sensor_enabled(sensor_id):
                disp_val = ((elapsed + phase) * 0.1) % 10 + random.uniform(-0.05, 0.05)
                # Slight scale differences per sensor for diversity
                scale = {
                    SensorId.DISP_1: 1.00,
                    SensorId.DISP_2: 1.10,
                    SensorId.DISP_3: 0.90,
                    SensorId.DISP_4: 1.20,
                    SensorId.DISP_5: 0.80,
                }[sensor_id]
                self._notify(sensor_id, time.time(), disp_val * scale)

    def _notify(self, sensor_id: SensorId, time: float, value: float):
        if self.want_zero:
            if not math.isnan(value):
                self.offsets[sensor_id.value] = value
                self.want_zero = False
                logger.info(f"Zeroed sensor {sensor_id}. New offset: {self.offsets[sensor_id.value]}")
        
        # Apply offset
        offset = self.offsets[sensor_id.value]
        corrected_value = value - offset

        # Publish raw value (before offset correction)
        data = SensorData(
            timestamp=time,
            sensor_id=sensor_id,
            value=corrected_value,
            raw_value=value,
            offset=offset
        )
        
        self.sensors[sensor_id.value] = data
        
        for func in self.notify_funcs:
            func(data)
            
        if self._calculate_arc(data) is not None:
            arc_data = self.sensors[SensorId.ARC.value]
            for func in self.notify_funcs:
                func(arc_data)
        
    def add_write_func(self, write_func: Callable[[SensorId, float, str], None]):
        """Add a write function to sensors task."""
        self._sensors_task.add_write_func(write_func)
            
    def add_func_notify(self, func: Callable[[SensorData], None]):
        """Add a function that will be called with new sensor data."""
        self.notify_funcs.append(func)

# Global instance
sensor_manager = SensorManager()
