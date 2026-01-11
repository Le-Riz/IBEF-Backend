# External libs
import asyncio
import logging

# Internal libs
from core.event_hub import init_event_hub
from core.services.serial_handler import serial_reader
from core.services.sensor_manager import sensor_manager
from core.services.test_manager import test_manager
from core.processing.data_processor import data_processor

logger = logging.getLogger(__name__)

class ServiceManager:
    
    async def start_services(self, emulation: bool = True):
        """Start global background services if not already started.
        Args:
            emulation: When True, start `SensorManager` in emulation mode and skip serial reader.
        """
        
        logger.info("Starting background services...")
        loop = asyncio.get_running_loop()
        
        # Init Event Hub
        init_event_hub(loop)
        
        # Data Processor (publishes processed_data at fixed rate)
        data_processor.start()
        
        # Sensor Manager
        sensor_manager.start(emulation=emulation)
        
        # Serial Reader only in hardware mode
        if not emulation:
            self.serial_task = loop.create_task(serial_reader(
                port="/dev/ttyACM0",
                baudrate=9600
            ))
        
        # Test Manager
        # Already initialized as singleton
        
        logger.info("Background services started.")

    def stop_services(self):
        """Stop background services."""
            
        sensor_manager.stop()
        if hasattr(self, 'serial_task'):
            self.serial_task.cancel()
            
        logger.info("Background services stopped.")

service_manager = ServiceManager()
