import os

import threading
import time
import logging
import math
import random
import asyncio
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
        self.emulated_sensors: list[SensorId] = []
        self.sensors: list[SensorData] = [SensorData(0.0, id, math.nan, math.nan) for id in SensorId]
        self._emulation_task: Optional[asyncio.Task] = None
        self.offsets: list[float] = [0.0 for _ in SensorId]
        self._serial_handlers: list[SerialHandler] = []
        self.queue: asyncio.Queue[tuple[SensorId, str, float]] = asyncio.Queue(maxsize=1024)
        self._sensors_task: SensorsTask = SensorsTask(self.queue)
        self.notify_funcs: list[Callable[[SensorData], None]] = []
        self.zero_requests: dict[SensorId, int] = {}
        self.sensor_ports: list[str] = [""] * len(SensorId)
        arc_config = config_loader.get_sensor_config(SensorId.ARC)
        self.arc_sensor_dependencies: list[SensorId] = []
        if isinstance(arc_config, calculatedConfigSensorData):
            self.arc_sensor_dependencies: list[SensorId] = [dep.id for dep in arc_config.dependencies]
        
        self.add_write_func(self._on_serial_data)

    def start(self, emulated_sensors: Optional[list[SensorId]] = None, sensor_ports: Optional[Dict[SensorId, tuple[str, int]]] = None):
        """Start sensor data acquisition."""
        emulated_sensors = emulated_sensors or []
        if self.running:
            if set(self.emulated_sensors) != set(emulated_sensors):
                self.stop()
            else:
                return

        self.emulated_sensors = emulated_sensors
        self.running = True
        logger.info(f"SensorManager started (Emulation: {[s.name for s in emulated_sensors]})")

        if self.emulated_sensors:
            self._emulation_task = asyncio.create_task(self._emulation_loop())
            
        if sensor_ports is None and not self.emulated_sensors:
            logger.warning("No sensor ports provided and no emulation requested.")
            
        if sensor_ports is not None:
            # Launch a SensorTask for each real sensor NOT in emulated_sensors
            for sensor_id, (port, baud) in sensor_ports.items():
                if sensor_id in self.emulated_sensors:
                    continue
                if port == "":
                    logger.warning(f"Sensor {sensor_id} has no assigned port, skipping...")
                    continue
                self.sensor_ports[sensor_id.value] = port
                full_port = PORT_PREFIX + port
                serial_handler = SerialHandler(sensor_id=sensor_id, port=full_port, queue=self.queue, baudrate=baud, serial_timeout=0.5)
                
                serial_handler.start()
                self._serial_handlers.append(serial_handler)
        
        self._sensors_task.start()

    def set_mode(self, emulated_sensors: list[SensorId]):
        """Set the operation mode (emulation or real hardware)."""
        if self.running:
            self.stop()
            self.start(emulated_sensors=emulated_sensors)
        else:
            self.emulated_sensors = emulated_sensors

    def is_sensor_connected(self, sensor_id: SensorId) -> bool:
        """
        Check if a sensor is currently connected.
        Handles ARC and emulation logic.
        """
        # Emulation mode: enabled in config = connected
        if sensor_id in self.emulated_sensors:
            
            return config_loader.is_sensor_enabled(sensor_id)
        
        # Hardware mode: check if we have a running SensorTask
        if sensor_id == SensorId.ARC:
            for sensor in self.arc_sensor_dependencies:
                if not self.is_sensor_connected(sensor):
                    return False
            return True
        
        port = self.sensor_ports[sensor_id.value]
        if not port:
            return False
            
        return os.path.exists(PORT_PREFIX + port)
    
    def stop(self):
        """Stop sensor data acquisition."""
        self.running = False
        if self._emulation_task:
            self._emulation_task.cancel()
            self._emulation_task = None
        # Stop all serial handlers
        for handler in self._serial_handlers:
            handler.stop()
        self._serial_handlers.clear()
        self._sensors_task.stop()
        logger.info("SensorManager stopped")

    async def _emulation_loop(self):
        start_time = time.time()
        while self.running and self.emulated_sensors:
            await self._emulate_data(start_time)
            await asyncio.sleep(0.1) # Rate limit

    def _on_serial_data(self, sensorId: SensorId, time_val: float, line: str):
        try:
            if sensorId == SensorId.FORCE:
                self._parse_force(sensorId, time_val, line)
                
            elif (sensorId == SensorId.DISP_1 or
                  sensorId == SensorId.DISP_2 or
                  sensorId == SensorId.DISP_3 or
                  sensorId == SensorId.DISP_4 or
                  sensorId == SensorId.DISP_5):
                self._parse_motion(sensorId, time_val, line)
                
        except Exception as e:
            logger.warning(f"Error parsing line: {line} -> {e}")

    def set_zero(self, sensor_id: SensorId):
        """Manually zero a sensor by updating its offset."""
        if sensor_id in SensorId:
            self.zero_requests[sensor_id] = 3

    def _parse_force(self, sensorId: SensorId, time: float, line: str):
        # ASC2 20945595 -165341 -1.527986e-01 -4.965955e+01 -0.000000e+00
        if not line or "ASC2" not in line:
            return
        
        parts = line.split()
        if len(parts) >= 5:
            try:
                val = float(parts[4]) # Calibrated value
                self._notify(sensorId, time, val)
            except ValueError:
                pass

    def _parse_motion(self, sensorId: SensorId, time: float, line: str):
        # 76 144 262 us SPC_VAL usSenderId=0x2E01 ulMicros=76071216 Val=0.000
        if not line or "SPC_VAL" not in line:
            return
        
        parts = line.split()
        sender_id = None
        val = None
        sending_timestamp_str = ""
        sending_timestamp = math.nan
        us_seen = False
        request_timestamp = math.nan
        for part in parts:
            if not us_seen:
                if part.endswith("us"):
                    sending_timestamp_str += part[:-2]
                    try:
                        sending_timestamp = float(sending_timestamp_str) / 1e6
                    except ValueError:
                        pass
                    us_seen = True
                else:
                    sending_timestamp_str += part
            elif part.startswith("usSenderId="):
                sender_id = part.split("=")[1]
            elif part.startswith("ulMicros="):
                try:
                    request_timestamp = float(part.split("=")[1]) / 1e6
                except ValueError:
                    pass
            elif part.startswith("Val="):
                try:
                    val = float(part.split("=")[1])
                except ValueError:
                    pass
        
        if not math.isnan(sending_timestamp) and not math.isnan(request_timestamp):
            time = time - (sending_timestamp - request_timestamp)
        else:
            time = math.nan
        
        if sender_id and val is not None and time is not math.nan:
            #####################################################################################
            #                                                                                   #
            #                               !!!!! WARNING !!!!!                                 #
            # TODO: Remove this workaround once sensors stop sending zero values randomly       #
            #                                                                                   #
            #####################################################################################
            if val < 0.02:
                val = math.nan
                logger.warning(f" LINE: {line}, val: {val}, time: {time}, sender_id: {sender_id}")
                
            self._notify(sensorId, time, val)

    def _calculate_arc(self, data: SensorData):
        if (data.sensor_id in self.arc_sensor_dependencies):
            disp1 = self.sensors[SensorId.DISP_1.value]
            disp2 = self.sensors[SensorId.DISP_2.value]
            disp3 = self.sensors[SensorId.DISP_3.value]
            arc = self.sensors[SensorId.ARC.value]
            
            if(not math.isnan(disp1.value) and
               not math.isnan(disp2.value) and
               not math.isnan(disp3.value)):
                arc.raw_value = disp1.raw_value - (disp2.raw_value + disp3.raw_value) / 2
                arc.value = disp1.value - (disp2.value + disp3.value) / 2
                arc.offset = disp1.offset - (disp2.offset + disp3.offset) / 2
                arc.timestamp = data.timestamp
                self.sensors[SensorId.ARC.value] = arc

                return arc
        return None

    async def _emulate_data(self, start_time):
        elapsed = time.time() - start_time

        from core.config_loader import config_loader

        # Emulate Force (Sine wave) only if enabled
        if SensorId.FORCE in self.emulated_sensors and config_loader.is_sensor_enabled(SensorId.FORCE):
            force_val = 500 + 500 * math.sin(elapsed) + random.uniform(-10, 10)
            line = f"ASC2 {int(elapsed * 1e6)} -39696 -3.577285e-02 {force_val:.6e} -0.000000e+00"
            if not self.queue.full():
                await self.queue.put((SensorId.FORCE, line, time.time()))

        # Emulate Displacement (Linear + Noise) with per-sensor phase offsets to avoid overlap
        phase_offsets = {
            SensorId.DISP_1: 0.0,
            SensorId.DISP_2: 1.5,
            SensorId.DISP_3: 3.0,
            SensorId.DISP_4: 4.5,
            SensorId.DISP_5: 6.0,
        }

        for sensor_id, phase in phase_offsets.items():
            if sensor_id in self.emulated_sensors and config_loader.is_sensor_enabled(sensor_id):
                disp_val = (((elapsed + phase) * 0.1) % 10 + random.uniform(-0.05, 0.05)) * {
                    SensorId.DISP_1: 1.00, SensorId.DISP_2: 1.10, SensorId.DISP_3: 0.90,
                    SensorId.DISP_4: 1.20, SensorId.DISP_5: 0.80
                }[sensor_id]
                
                elapsed_us = int(elapsed * 1e6)
                line = f"{elapsed_us} us SPC_VAL usSenderId=0x2E01 ulMicros={elapsed_us} Val={disp_val:.3f}"
                if not self.queue.full():
                    await self.queue.put((sensor_id, line, time.time()))

    def _notify(self, sensor_id: SensorId, time: float, value: float):
        if self.zero_requests.get(sensor_id, 0) > 0:
            if not math.isnan(value):
                self.offsets[sensor_id.value] = value
                self.zero_requests[sensor_id] = 0
                logger.info(f"Zeroed sensor {sensor_id}. New offset: {self.offsets[sensor_id.value]}")
            else:
                self.zero_requests[sensor_id] -= 1
                if self.zero_requests[sensor_id] == 0:
                    logger.warning(f"Failed to zero sensor {sensor_id} after 3 attempts with NaN values.")
        
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
