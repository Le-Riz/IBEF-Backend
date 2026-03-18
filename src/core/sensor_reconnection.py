import asyncio
import logging
import queue
import time
from typing import Callable, Optional
from dataclasses import dataclass, field
from enum import Enum

from core.models.sensor_enum import SensorId
from core.services.serial_handler import SerialHandler

logger = logging.getLogger(__name__)

class SensorsTask:
    def __init__(self, queue: queue.Queue[tuple[SensorId, str, float]]):
        self.queue = queue
        self.write_func: list[Callable[[SensorId, float, str], None]] = []  # list of async functions to write sensor data
        self.serial_handlers: list[SerialHandler] = []
        self._running = False
        

    async def run(self):
        self._running = True
        while self._running:
            try:
                data = self.queue.get(timeout=1.0)
                
                if data is None:
                    continue
                
                data_time = data[2]
                sensor_id = data[0]
                value = data[1]
                
                if data is not None:
                    for write in self.write_func:
                        write(sensor_id, data_time, value)
            except Exception as e:
                await asyncio.sleep(0.1)

    def start(self):
        
        asyncio.create_task(self.run())
        from signal import SIGINT, SIGTERM
        for sig in (SIGINT, SIGTERM):
            asyncio.get_event_loop().add_signal_handler(sig, self.stop)


    def stop(self):
        self._running = False
    
    def add_write_func(self, write_func: Callable[[SensorId, float, str], None]):
        self.write_func.append(write_func)
