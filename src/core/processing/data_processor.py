import time
import asyncio
import logging
import math
from collections import deque
from typing import Callable, Optional, Any
from core.models.sensor_data import SensorData
from core.models.sensor_enum import SensorId
from core.services.sensor_manager import sensor_manager

logger = logging.getLogger(__name__)

# Config
PROCESSING_RATE = 4.0 # 4 Hz common time step

class DataProcessor:
    def __init__(self):
        self.running = False
        self.history_values: list[deque[SensorData]] = [deque(maxlen=2) for _ in SensorId]
        self.nan_counts: list[int] = [0 for _ in SensorId]
        self._task: Optional[asyncio.Task] = None
        self.processing_data: Callable[[list[SensorData]], None] = lambda x: None  # Placeholder, can be set by UI or TestManager
        self.raw_processing_data: Callable[[SensorData], None] = lambda x: None  # Placeholder for raw data processing
        
        # Subscribe to internal raw updates to update cache
        sensor_manager.add_func_notify(self._on_raw_update)

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

    def _on_raw_update(self, data: SensorData):
        # Call the raw processing function
        self.raw_processing_data(data)

        if(not math.isnan(data.value)):
            self.nan_counts[data.sensor_id.value] = 0
            self.history_values[data.sensor_id.value].append(data)
        else:
            self.nan_counts[data.sensor_id.value] += 1
            
            if self.nan_counts[data.sensor_id.value] > 2:
                logger.warning(f"[DataProcessor] Sensor {data.sensor_id} has sent {self.nan_counts[data.sensor_id.value]} consecutive NaN values.")
                self.history_values[data.sensor_id.value].append(SensorData(float('nan'), data.sensor_id, data.timestamp, data.raw_value))
            else:
                extrapolated = self.extrapolated_value(data.sensor_id, data.timestamp)
                self.history_values[data.sensor_id.value].append(extrapolated)

    def extrapolated_value(self, sensor_id: SensorId, time_extrapolate: float) -> SensorData:
        value = SensorData(0.0, sensor_id, float('nan'), 0.0, float('nan'))
        
        history = self.history_values[sensor_id.value]
        
        if len(history) == 2:
            older, newer = history[0], history[1]
            
            if (math.isnan(history[0].value) or
                math.isnan(history[1].value)):
                value.timestamp = time_extrapolate
            
            elif not sensor_manager.is_sensor_connected(sensor_id):
                value = SensorData(
                    timestamp=time_extrapolate,
                    sensor_id=sensor_id,
                    value=float('nan'),
                    raw_timestamp=newer.raw_timestamp,
                    raw_value=float('nan')
                )
                
            else:
                slope = (newer.value - older.value) / (newer.timestamp - older.timestamp)
                predicted_value = newer.value + slope * (time_extrapolate - newer.timestamp)
                
                extrapolated = SensorData(
                    timestamp=time_extrapolate,
                    sensor_id=sensor_id,
                    value=predicted_value,
                    raw_timestamp=newer.raw_timestamp,
                    raw_value=newer.raw_value
                )
                value = extrapolated
                
        elif len(history) == 1:
            value = SensorData(
                    timestamp=time_extrapolate,
                    sensor_id=sensor_id,
                    value=history[0].value,
                    raw_timestamp=history[0].raw_timestamp,
                    raw_value=history[0].raw_value
                )
        else:
            value = SensorData(
                    timestamp=time_extrapolate,
                    sensor_id=sensor_id,
                    value=float('nan'),
                    raw_timestamp=time_extrapolate,
                    raw_value=float('nan')
                )
        return value

    async def _process_loop(self):
        interval = 1.0 / PROCESSING_RATE
        while self.running:
            start_loop = time.time()
            
            values_copy = [SensorData(0.0, sensor_id, float('nan'), 0.0, float('nan')) for sensor_id in SensorId]
            for sensor_id in SensorId:
                values_copy[sensor_id.value] = self.extrapolated_value(sensor_id, start_loop)

            if(not math.isnan(values_copy[SensorId.DISP_1.value].value) and
               not math.isnan(values_copy[SensorId.DISP_2.value].value) and
               not math.isnan(values_copy[SensorId.DISP_3.value].value)):
                values_copy[SensorId.ARC.value].raw_value = values_copy[SensorId.DISP_1.value].raw_value - (values_copy[SensorId.DISP_2.value].raw_value + values_copy[SensorId.DISP_3.value].raw_value) / 2
                values_copy[SensorId.ARC.value].value = values_copy[SensorId.DISP_1.value].value - (values_copy[SensorId.DISP_2.value].value + values_copy[SensorId.DISP_3.value].value) / 2
            
            # Emit processed frame for UI and Recorder
            # event_hub.send_all_on_topic("processed_data", values_copy)
            self.processing_data(values_copy)
            
            # Sleep remainder
            elapsed = time.time() - start_loop
            delay = max(0, interval - elapsed)
            await asyncio.sleep(delay)
            
    def set_processing_function(self, func: Callable[[list[SensorData]], None]):
        self.processing_data = func

data_processor = DataProcessor()
