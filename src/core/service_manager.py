# External libs
import asyncio
import logging

# Internal libs
from core.event_hub import init_event_hub
from core.models.config_data import configSensorData
from core.models.sensor_enum import SensorId
from core.services.sensor_manager import sensor_manager
from core.services.test_manager import test_manager
from core.processing.data_processor import data_processor
from core.config_loader import config_loader



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
        # Sensor Manager: in hardware mode, pass detected sensor ports/bauds
        if emulation:
            sensor_manager.start(emulation=True)
        else:
            # Get sensor baud rates and ports from config
            sensor_ports = {}
            for configItem in config_loader.get_all_sensors().items():
                if isinstance(configItem[1], configSensorData):
                    sensor_ports[configItem[0]] = (configItem[1].serialId, configItem[1].baud)
            sensor_manager.start(emulation=False, sensor_ports=sensor_ports)
        # Test Manager (already singleton)
        logger.info("Background services started.")

    def stop_services(self):
        """Stop background services."""
        self.running = False
        sensor_manager.stop()
        logger.info("Background services stopped.")

service_manager = ServiceManager()
