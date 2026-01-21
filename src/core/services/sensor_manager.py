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
from core.sensor_reconnection import sensor_reconnection_manager

logger = logging.getLogger(__name__)

class SensorManager:
    """
    Manages sensor data acquisition from serial ports (via EventHub) or emulation.
    """
    def __init__(self):
        self.running = False
        self.emulation_mode = False
        # Store current sensor values: List indexed by SensorId.value
        self.sensors: list[float] = [0.0 for _ in SensorId]
        self._thread: Optional[threading.Thread] = None
        self.motion_sensor_map: Dict[str, SensorId] = {}
        # Store offsets: List indexed by SensorId.value
        self.offsets: list[float] = [0.0 for _ in SensorId]

        # Preload mappings from configuration if present
        self._load_motion_sensor_mapping()
        
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
            sensor_id = self.motion_sensor_map.get(sender_id)

            # If not configured, assign dynamically to next available DISP
            if sensor_id is None:
                sensor_id = self._assign_motion_sensor(sender_id)
                if sensor_id:
                    logger.info(f"Assigned motion sender {sender_id} to {sensor_id.name}")

            if sensor_id:
                self._notify(sensor_id, val)

    def _load_motion_sensor_mapping(self):
        """Load pre-defined motion sensor mappings from config."""
        sensors_config = config_loader.get_all_sensors()
        for name, sensor_config in sensors_config.items():
            if not name.startswith("DISP"):
                continue
            sender_id = sensor_config.get("sender_id")
            if not sender_id:
                continue
            try:
                sensor_id = SensorId[name]
            except KeyError:
                continue
            self.motion_sensor_map[sender_id] = sensor_id
        if self.motion_sensor_map:
            logger.info(f"Loaded {len(self.motion_sensor_map)} motion sensor mappings from config")

    def _assign_motion_sensor(self, sender_id: str) -> Optional[SensorId]:
        """Assign sender_id to next available DISP sensor when not in config."""
        disp_order = [
            SensorId.DISP_1,
            SensorId.DISP_2,
            SensorId.DISP_3,
            SensorId.DISP_4,
            SensorId.DISP_5,
        ]
        for disp_sensor in disp_order:
            if disp_sensor not in self.motion_sensor_map.values():
                self.motion_sensor_map[sender_id] = disp_sensor
                return disp_sensor
        return None

    def _emulate_data(self, start_time):
        elapsed = time.time() - start_time
        
        # Emulate Force (Sine wave)
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

        # Record data reception for health monitoring (in hardware mode)
        if not self.emulation_mode:
            sensor_name = sensor_id.name
            sensor_reconnection_manager.record_sensor_data(sensor_name)

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
