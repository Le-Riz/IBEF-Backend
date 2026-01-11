import threading
import time
import logging
import math
import random
from typing import Dict, Optional

from core.models.sensor_data import SensorData
from core.models.sensor_enum import SensorId
from core.event_hub import event_hub

logger = logging.getLogger(__name__)

class SensorManager:
    """
    Manages sensor data acquisition from serial ports (via EventHub) or emulation.
    """
    def __init__(self):
        self.running = False
        self.emulation_mode = False
        # Store current sensor values: List indexed by SensorId.value - 1
        self.sensors: list[float] = [0.0 for _ in SensorId]
        self._thread: Optional[threading.Thread] = None
        self.motion_sensor_map: Dict[str, SensorId] = {}
        # Store offsets: List indexed by SensorId.value - 1
        self.offsets: list[float] = [0.0 for _ in SensorId]
        
        # Subscribe to serial data from the global handler
        # Note: The handler signature for PubSubHub is (topic, message)
        event_hub.subscribe("serial_data", self._on_serial_data)
        event_hub.subscribe("sensor_command", self._on_command)

    def start(self, emulation=False):
        """Start sensor data acquisition."""
        if self.running:
            # If already running, check if mode changed
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

    def set_mode(self, emulation: bool):
        """Set the operation mode (emulation or real hardware)."""
        if self.running:
            self.stop()
            self.start(emulation)
        else:
            self.emulation_mode = emulation

    def stop(self):
        """Stop sensor data acquisition."""
        self.running = False
        if self._thread:
            self._thread.join()
            self._thread = None
        logger.info("SensorManager stopped")

    def _loop(self):
        start_time = time.time()
        while self.running:
            if self.emulation_mode:
                self._emulate_data(start_time)
            time.sleep(0.1) # Rate limit

    def _on_serial_data(self, topic, line):
        # Only process if NOT in emulation mode
        if not self.emulation_mode:
            try:
                if "ASC2" in line:
                    self._parse_force(line)
                elif "SPC_VAL" in line:
                    self._parse_motion(line)
            except Exception as e:
                logger.warning(f"Error parsing line: {line} -> {e}")

    def _on_command(self, topic, command):
        if command.get("action") == "zero":
            sensor_id = command.get("sensor_id")
            if isinstance(sensor_id, SensorId):
                current_val = self.sensors[sensor_id.value]
                old_offset = self.offsets[sensor_id.value]
                self.offsets[sensor_id.value] = old_offset + current_val
                logger.info(f"Zeroed sensor {sensor_id.name}. New offset: {self.offsets[sensor_id.value]}")

    def _parse_force(self, line):
        # ASC2 20945595 -165341 -1.527986e-01 -4.965955e+01 -0.000000e+00
        parts = line.split()
        if len(parts) >= 5:
            try:
                val = float(parts[4]) # Calibrated value
                self._notify(SensorId.FORCE, val)
            except ValueError:
                pass

    def _parse_motion(self, line):
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
            # Map sender_id to DISP_X
            if sender_id not in self.motion_sensor_map:
                # Assign next available DISP
                count = len(self.motion_sensor_map)
                if count < 3:
                    self.motion_sensor_map[sender_id] = [SensorId.DISP_1, SensorId.DISP_2, SensorId.DISP_3][count]
            
            sensor_id = self.motion_sensor_map.get(sender_id)
            if sensor_id:
                self._notify(sensor_id, val)

    def _emulate_data(self, start_time):
        elapsed = time.time() - start_time
        
        # Emulate Force (Sine wave)
        force_val = 500 + 500 * math.sin(elapsed) + random.uniform(-10, 10)
        self._notify(SensorId.FORCE, force_val)

        # Emulate Displacement (Linear + Noise)
        disp_val = (elapsed * 0.1) % 10 + random.uniform(-0.05, 0.05)
        self._notify(SensorId.DISP_1, disp_val)
        self._notify(SensorId.DISP_2, disp_val * 1.1)
        self._notify(SensorId.DISP_3, disp_val * 0.9)

    def _notify(self, sensor_id: SensorId, value: float):
        # Apply offset
        offset = self.offsets[sensor_id.value]
        corrected_value = value - offset

        data = SensorData(
            timestamp=time.time(),
            sensor_id=sensor_id,
            value=corrected_value,
        )
        self.sensors[sensor_id.value] = corrected_value
        event_hub.send_all_on_topic("sensor_update", data)

# Global instance
sensor_manager = SensorManager()
