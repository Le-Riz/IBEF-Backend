import asyncio
import logging
import time
import serial
from core.models.sensor_enum import SensorId

logger = logging.getLogger(__name__)

class SerialHandler:
    def __init__(self, 
        sensor_id: SensorId,
        port: str,
        queue: asyncio.Queue[tuple[SensorId, str, float]],
        baudrate: int = 9600,
        serial_timeout: float = 0.5,
    ):
        
        self.baudrate = baudrate
        self.port = port
        self.timeout = serial_timeout
        self.serial = None
        self.sensor_id = sensor_id
        self.queue = queue
        self.running = False
        
    def start(self):
        self.running = True
        asyncio.create_task(self.read_serial())
    
    def stop(self):
        self.running = False
        if self.serial and self.serial.is_open:
            self.serial.close()
    
    async def read_serial(self):
        while self.running:
            try:
                if self.serial is None:
                    try:
                        self.serial = await asyncio.to_thread(
                            serial.Serial, port=self.port, baudrate=self.baudrate, timeout=self.timeout
                        )
                        logger.info(f"SerialHandler for {self.sensor_id.name} reconnected to {self.port} at {self.baudrate} baud.")
                    except Exception as e:
                        logger.error(f"Failed to reconnect SerialHandler for {self.sensor_id.name} on {self.port}: {e}")
                        await asyncio.sleep(0.5)
                        continue
                
                line = await asyncio.to_thread(self.serial.readline)
                if line:
                    decoded_line = line.decode('utf-8', errors='ignore').strip()
                    if self.queue.full():
                        try:
                            self.queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    await self.queue.put((self.sensor_id, decoded_line, time.time()))
                    
            except Exception as e:
                logger.error(f"Error reading from serial port for {self.sensor_id}: {e}")
                await asyncio.sleep(1.0)