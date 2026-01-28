import time
import asyncio
import logging
from typing import Dict, Optional, Any
from core.event_hub import event_hub
from core.models.sensor_data import SensorData
from core.models.sensor_enum import SensorId

logger = logging.getLogger(__name__)

# Config
PROCESSING_RATE = 4.0 # 4 Hz common time step

class DataProcessor:
    def __init__(self):
        self.running = False
        self.latest_values: list[float] = [0.0 for _ in SensorId]
        self._task: Optional[asyncio.Task] = None
        
        # Subscribe to internal raw updates to update cache
        event_hub.subscribe("sensor_update", self._on_raw_update)

    def start(self):
        if self.running: 
            return
        self.running = True
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._process_loop())
        logger.info("DataProcessor started")

    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("DataProcessor stopped")

    def _on_raw_update(self, topic, data: SensorData):
        self.latest_values[data.sensor_id.value] = data.value

    async def _process_loop(self):
        interval = 1.0 / PROCESSING_RATE
        while self.running:
            start_loop = time.time()
            
            # Create a frame
            # TODO: Linear interpolation if we wanted to be fancy, but Sample & Hold is sufficient 
            # and causal for real-time monitoring.
            
            # Calculate ARC (circular deflection): DISP_1 - (DISP_2 + DISP_3) / 2
            values_copy = self.latest_values.copy()
            arc_value = values_copy[SensorId.DISP_1.value] - (values_copy[SensorId.DISP_2.value] + values_copy[SensorId.DISP_3.value]) / 2
            values_copy[SensorId.ARC.value] = arc_value
            
            frame = {
                "timestamp": start_loop,
                "values": values_copy,
            }
            
            # Emit processed frame for UI and Recorder
            event_hub.send_all_on_topic("processed_data", frame)
            
            # Sleep remainder
            elapsed = time.time() - start_loop
            delay = max(0, interval - elapsed)
            await asyncio.sleep(delay)

data_processor = DataProcessor()
