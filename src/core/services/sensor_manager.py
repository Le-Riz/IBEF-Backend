import threading
import time
import logging
import math
import random
from typing import Dict, Optional

from core.config_loader import config_loader
from core.models.sensor_data import SensorData
from core.models.sensor_enum import SensorId
from core.event_hub import event_hub
from core.sensor_reconnection import SensorTask
from core.services.serial_handler import create_serial_sensor_task

logger = logging.getLogger(__name__)
PORT_PREFIX = "/dev/serial/by-id/"

class SensorManager:
    """
    Manages sensor data acquisition from serial ports (via EventHub) or emulation.
    """
    def __init__(self):
        self.running = False
        self.emulation_mode = False
        self.sensors: list[float] = [0.0 for _ in SensorId]
        self._thread: Optional[threading.Thread] = None
        self.offsets: list[float] = [0.0 for _ in SensorId]
        self._sensor_tasks: Dict[SensorId, SensorTask] = {}
        event_hub.subscribe("serial_data", self._on_serial_data)
        event_hub.subscribe("sensor_command", self._on_command)

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
                full_port = PORT_PREFIX + port
                task = create_serial_sensor_task(sensor_id, full_port, baud)
                task.start()
                self._sensor_tasks[sensor_id] = task

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
        if sensor_id.name == "ARC":
            return (
                self.is_sensor_connected(SensorId.DISP_1)
                and self.is_sensor_connected(SensorId.DISP_2)
                and self.is_sensor_connected(SensorId.DISP_3)
            )
        return sensor_id in self._sensor_tasks and self._sensor_tasks[sensor_id].is_connected()
    
    def stop(self):
        """Stop sensor data acquisition."""
        self.running = False
        if self._thread:
            self._thread.join()
            self._thread = None
        # Stop all sensor tasks
        for task in self._sensor_tasks.values():
            task.stop()
        self._sensor_tasks.clear()
        logger.info("SensorManager stopped")

    def _loop(self):
        start_time = time.time()
        while self.running:
            if self.emulation_mode:
                self._emulate_data(start_time)
            time.sleep(0.1) # Rate limit

    def _on_serial_data(self, topic: str, line: tuple[SensorId, str]):
        # Only process if NOT in emulation mode
        if not self.emulation_mode:
            try:
                sensorId, line_str = line
                if sensorId == SensorId.FORCE:
                    self._parse_force(sensorId, line_str)
                    
                elif (sensorId == SensorId.DISP_1 or
                      sensorId == SensorId.DISP_2 or
                      sensorId == SensorId.DISP_3 or
                      sensorId == SensorId.DISP_4 or
                      sensorId == SensorId.DISP_5):
                    self._parse_motion(sensorId, line_str)
                    
            except Exception as e:
                logger.warning(f"Error parsing line: {line} -> {e}")

    def _on_command(self, topic, command):
        if command.get("action") == "zero":
            sensor_id = command.get("sensor_id")
            if isinstance(sensor_id, SensorId):
                current_val = self.sensors[sensor_id.value]
                old_offset = self.offsets[sensor_id.value]
                self.offsets[sensor_id.value] = old_offset + current_val
                logger.info(f"Zeroed sensor {sensor_id}. New offset: {self.offsets[sensor_id.value]}")

    def _parse_force(self, sensorId: SensorId, line: str):
        # ASC2 20945595 -165341 -1.527986e-01 -4.965955e+01 -0.000000e+00
        parts = line.split()
        if len(parts) >= 5:
            try:
                val = float(parts[4]) # Calibrated value
                self._notify(sensorId, val)
            except ValueError:
                pass

    def _parse_motion(self, sensorId: SensorId, line: str):
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
            self._notify(sensorId, val)

    def _emulate_data(self, start_time):
        elapsed = time.time() - start_time

        from core.config_loader import config_loader

        # Emulate Force (Sine wave) only if enabled
        if config_loader.is_sensor_enabled(SensorId.FORCE):
            force_val = 500 + 500 * math.sin(elapsed) + random.uniform(-10, 10)
            self._notify(SensorId.FORCE, force_val)

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
                self._notify(sensor_id, disp_val * scale)

    def _notify(self, sensor_id: SensorId, value: float):
        # Apply offset
        offset = self.offsets[sensor_id.value]
        corrected_value = value - offset



        # Publish raw value (before offset correction)
        raw_data = SensorData(
            timestamp=time.time(),
            sensor_id=sensor_id,
            value=value,  # Raw uncorrected value
        )
        event_hub.send_all_on_topic("sensor_raw_update", raw_data)

        # Publish corrected value
        data = SensorData(
            timestamp=time.time(),
            sensor_id=sensor_id,
            value=corrected_value,
        )
        self.sensors[sensor_id.value] = corrected_value
        event_hub.send_all_on_topic("sensor_update", data)

# Global instance
sensor_manager = SensorManager()
