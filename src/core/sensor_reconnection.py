import asyncio
import logging
import time
from typing import Callable, Optional
from dataclasses import dataclass, field
from enum import Enum

from core.models.sensor_enum import SensorId
from core.services.serial_handler import SerialHandler

logger = logging.getLogger(__name__)

class SensorsTask:
    def __init__(self, queue: asyncio.Queue[tuple[SensorId, str, float]]):
        self.queue = queue
        self.write_func: list[Callable[[SensorId, float, str], None]] = []  # list of async functions to write sensor data
        self.serial_handlers: list[SerialHandler] = []
        self._running = False
        

    async def run(self):
        logger.info("SensorsTask started.")
        self._running = True
        while self._running:
            try:
                data = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                if data is None:
                    continue
                
                # Dispatch synchronous callbacks in a thread executor
                # to avoid blocking the asyncio event loop
                await asyncio.to_thread(self._dispatch, data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"SensorsTask error: {e}")
                await asyncio.sleep(0.1)

    def _dispatch(self, data: tuple) -> None:
        """Process a single frame's callbacks (runs in thread executor)."""
        sensor_id = data[0]
        value = data[1]
        data_time = data[2]
        for write in self.write_func:
            write(sensor_id, data_time, value)

    def start(self):
        print("Starting SensorsTask...")
        asyncio.create_task(self.run())


    def stop(self):
        print("Stopping SensorsTask...")
        self._running = False
    
    def add_write_func(self, write_func: Callable[[SensorId, float, str], None]):
        self.write_func.append(write_func)
