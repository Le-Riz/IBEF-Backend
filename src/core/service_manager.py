# External libs
import asyncio
import logging

# Internal libs
from core.models.config_data import configSensorData
from core.services.sensor_manager import sensor_manager
from core.config_loader import config_loader
from core.models.sensor_enum import SensorId



logger = logging.getLogger(__name__)

class ServiceManager:
    
    async def start_services(self, emulation: list[SensorId] = None):
        """Start global background services if not already started.
        Args:
            emulation: List of sensors to emulate.
        """
        logger.info("Starting background services...")
        if emulation is None:
            emulation = []
        
        # Get sensor baud rates and ports from config
        sensor_ports = {}
        for configItem in config_loader.get_all_sensors().items():
            if isinstance(configItem[1], configSensorData):
                sensor_ports[configItem[0]] = (configItem[1].serialId, configItem[1].baud)
                
        sensor_manager.start(emulated_sensors=emulation, sensor_ports=sensor_ports)
        # Test Manager (already singleton)
        logger.info("Background services started.")

    def stop_services(self):
        """Stop background services."""
        self.running = False
        sensor_manager.stop()
        logger.info("Background services stopped.")

service_manager = ServiceManager()
