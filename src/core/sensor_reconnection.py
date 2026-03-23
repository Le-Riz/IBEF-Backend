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
    """
    Consumer that drains the shared thread-safe queue.Queue and dispatches
    data to registered callbacks.
    
    Bridges the threading world (serial readers) back to the asyncio world
    (FastAPI) by using asyncio.to_thread for the blocking queue.get().
    """

    def __init__(self, data_queue: queue.Queue):
        self.queue = data_queue
        self.write_func: list[Callable[[SensorId, float, str], None]] = []
        self.serial_handlers: list[SerialHandler] = []
        self._running = False
        

    async def run(self):
        logger.info("SensorsTask started.")
        self._running = True
        while self._running:
            try:
                # Bridge: block in a thread executor waiting for data from
                # the thread-safe queue, yielding the asyncio event loop
                data = await asyncio.to_thread(self._blocking_get)
                if data is None:
                    continue
                
                # Dispatch callbacks in a thread executor as well,
                # keeping the event loop free
                await asyncio.to_thread(self._dispatch, data)
            except Exception as e:
                logger.error(f"SensorsTask error: {e}")
                await asyncio.sleep(0.1)

    def _blocking_get(self):
        """
        Blocking get from queue.Queue with a 1-second timeout.
        Returns None on timeout (allows checking self._running).
        Runs in the asyncio thread executor.
        """
        try:
            return self.queue.get(timeout=1.0)
        except queue.Empty:
            return None

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
