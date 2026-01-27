
# SIMPLIFIED SENSOR RECONNECTION LOGIC
import asyncio
import logging
import time
from typing import Callable, Optional
from dataclasses import dataclass, field
from enum import Enum

from core.models.sensor_enum import SensorId

logger = logging.getLogger(__name__)

class SensorState(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"

@dataclass
class SensorHealthMonitor:
    sensor_id: SensorId
    max_silence_time: float = 5.0
    initial_reconnect_delay: float = 1.0
    max_reconnect_delay: float = 10.0
    backoff_multiplier: float = 1.5
    last_data_time: float = field(default_factory=time.time)
    state: SensorState = SensorState.CONNECTED
    reconnect_attempts: int = 0
    current_backoff_delay: float = field(default=0.0)

    def __post_init__(self):
        self.current_backoff_delay = self.initial_reconnect_delay
        self.last_data_time = time.time()

    def record_data(self):
        self.last_data_time = time.time()
        if self.state != SensorState.CONNECTED:
            logger.info(f"✓ {self.sensor_id} reconnected!")
            self.state = SensorState.CONNECTED
            self.reconnect_attempts = 0
            self.current_backoff_delay = self.initial_reconnect_delay

    def check_silence(self) -> bool:
        return (time.time() - self.last_data_time) > self.max_silence_time

    def mark_disconnected(self):
        if self.state != SensorState.DISCONNECTED:
            logger.warning(f"⚠ {self.sensor_id} disconnected (no data for {time.time() - self.last_data_time:.1f}s)")
            self.state = SensorState.DISCONNECTED
            self.reconnect_attempts = 0
            self.current_backoff_delay = self.initial_reconnect_delay

    def get_next_retry_delay(self) -> float:
        delay = self.current_backoff_delay
        self.current_backoff_delay = min(self.current_backoff_delay * self.backoff_multiplier, self.max_reconnect_delay)
        return delay

    def reset_backoff(self):
        self.current_backoff_delay = self.initial_reconnect_delay
        self.reconnect_attempts = 0


class SensorTask:
    def __init__(self, sensor_id: SensorId, read_func: Callable, max_silence_time: float = 5.0, monitor: Optional[SensorHealthMonitor] = None):
        self.sensor_id = sensor_id
        self.read_func = read_func  # async function to read sensor data
        self.monitor = monitor if monitor is not None else SensorHealthMonitor(sensor_id, max_silence_time=max_silence_time)
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def run(self):
        self._running = True
        while self._running:
            try:
                data = await self.read_func()
                if data is not None:
                    self.monitor.record_data()
                else:
                    # No data received, check silence
                    if self.monitor.check_silence():
                        self.monitor.mark_disconnected()
                        # Backoff before next read
                        delay = self.monitor.get_next_retry_delay()
                        logger.info(f"[Sensor {self.sensor_id}] Backing off for {delay:.1f}s before next read...")
                        await asyncio.sleep(delay)
                    else:
                        await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"[Sensor {self.sensor_id}] Exception: {e}")
                await asyncio.sleep(1.0)

    def start(self):
        if not self._task:
            self._task = asyncio.create_task(self.run())

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    def is_connected(self) -> bool:
        return self.monitor.state == SensorState.CONNECTED

# Example usage:
# async def read_sensor():
#     ...
# sensor_task = SensorTask(SensorId.FORCE, read_sensor)
# sensor_task.start()
