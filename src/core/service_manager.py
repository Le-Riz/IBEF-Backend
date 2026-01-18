# External libs
import asyncio
import logging

# Internal libs
from core.event_hub import init_event_hub
from core.services.serial_handler import serial_reader
from core.services.sensor_manager import sensor_manager
from core.services.test_manager import test_manager
from core.processing.data_processor import data_processor
from core.config_loader import config_loader
from core.port_detector import port_detector
from core.sensor_reconnection import sensor_reconnection_manager

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
        
        # Set emulation mode for sensor reconnection manager
        sensor_reconnection_manager.emulation_mode = emulation
        
        # Serial Reader only in hardware mode
        if not emulation:
            # Get sensor baud rates from config
            sensor_bauds = {}
            for sensor_name, sensor_config in config_loader.get_all_sensors().items():
                sensor_bauds[sensor_name] = sensor_config.get("baud", 9600)
            
            # Setup health monitoring for reconnections
            for sensor_name in sensor_bauds.keys():
                sensor_reconnection_manager.add_sensor(sensor_name, max_silence_time=5.0)
            
            # Register reconnection callback
            async def reconnect_sensor(sensor_name: str) -> bool:
                """Attempt to reconnect a specific sensor."""
                logger.info(f"Attempting to reconnect {sensor_name}...")
                detected = port_detector.auto_detect_sensors({sensor_name: sensor_bauds[sensor_name]})
                
                if sensor_name in detected:
                    sensor_info = detected[sensor_name]
                    logger.info(f"✓ Re-detected {sensor_name} on {sensor_info.port} @ {sensor_info.baud} baud")
                    
                    # Start serial reader for the reconnected sensor
                    task = loop.create_task(serial_reader(
                        port=sensor_info.port,
                        baudrate=sensor_info.baud,
                        sensor_name=sensor_name
                    ))
                    # Store task for later cleanup if needed
                    if not hasattr(self, 'sensor_tasks_map'):
                        self.sensor_tasks_map = {}
                    self.sensor_tasks_map[sensor_name] = task
                    return True
                else:
                    logger.warning(f"✗ Could not re-detect {sensor_name}")
                    return False
            
            for sensor_name in sensor_bauds.keys():
                sensor_reconnection_manager.register_reconnection_callback(sensor_name, reconnect_sensor)
            
            # Start health monitoring
            monitor_task = loop.create_task(sensor_reconnection_manager.start_monitoring())
            self.monitor_task = monitor_task
            
            # Auto-detect sensors initially
            logger.info("Detecting connected sensors...")
            detected_sensors = port_detector.auto_detect_sensors(sensor_bauds)
            
            if not detected_sensors:
                logger.warning("No sensors detected. Check connections and baud rates.")
            else:
                # Start serial readers for all detected sensors
                self.serial_tasks = []
                if not hasattr(self, 'sensor_tasks_map'):
                    self.sensor_tasks_map = {}
                
                for sensor_name, sensor_info in detected_sensors.items():
                    logger.info(f"Starting serial reader for {sensor_name}: {sensor_info.port} @ {sensor_info.baud} baud")
                    task = loop.create_task(serial_reader(
                        port=sensor_info.port,
                        baudrate=sensor_info.baud,
                        sensor_name=sensor_name
                    ))
                    self.serial_tasks.append(task)
                    self.sensor_tasks_map[sensor_name] = task
        
        # Test Manager
        # Already initialized as singleton
        
        logger.info("Background services started.")

    def stop_services(self):
        """Stop background services."""
            
        sensor_manager.stop()
        
        # Stop health monitoring
        asyncio.create_task(sensor_reconnection_manager.stop_monitoring())
        
        if hasattr(self, 'serial_tasks'):
            for task in self.serial_tasks:
                task.cancel()
        
        if hasattr(self, 'monitor_task'):
            self.monitor_task.cancel()
        
        if hasattr(self, 'sensor_tasks_map'):
            for task in self.sensor_tasks_map.values():
                if task and not task.done():
                    task.cancel()
            
        logger.info("Background services stopped.")

service_manager = ServiceManager()
