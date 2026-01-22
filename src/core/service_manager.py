# External libs
import asyncio
import logging

# Internal libs
from core.event_hub import init_event_hub
from core.models.sensor_enum import SensorId
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
            # Get sensor baud rates from config — only include real hardware sensors
            sensor_bauds = {}
            for sensor_id, sensor_config in config_loader.get_all_sensors().items():
                # If a sensor has no explicit 'baud' field, treat it as a virtual/calculated sensor
                sensor_bauds[sensor_id] = sensor_config.baud
            
            # Store detected sensor info for reconnection (baud may differ from config)
            detected_sensor_info = {}  # sensor_id -> (port, baud)
            missing_sensors_state = {}  # Track which sensors were missing (for state change logging)
            reconnection_failure_state = {}  # Track failed reconnection attempts (for state change logging)
            
            # Register reconnection callback
            async def reconnect_sensor(sensor_id: SensorId) -> bool:
                """Attempt to reconnect a specific sensor."""
                logger.info(f"Attempting to reconnect {sensor_id.name}...")
                
                # Use detected baud if available, otherwise use configured baud
                baud_to_use = sensor_bauds[sensor_id]
                if sensor_id in detected_sensor_info:
                    old_port, detected_baud = detected_sensor_info[sensor_id]
                    baud_to_use = detected_baud
                else:
                    old_port = None
                
                # Try to detect the sensor
                detected = port_detector.auto_detect_sensors(
                    {sensor_id: baud_to_use},
                    sensor_configs=config_loader.get_all_sensors(),
                    verbose=False
                )
                
                if sensor_id in detected:
                    sensor_info = detected[sensor_id]
                    logger.info(f"✓ Re-detected {sensor_id.name} on {sensor_info.port} @ {sensor_info.baud} baud")
                    detected_sensor_info[sensor_id] = (sensor_info.port, sensor_info.baud)
                    reconnection_failure_state[sensor_id] = False  # Clear failure state
                    
                    # Start serial reader for the reconnected sensor
                    task = loop.create_task(serial_reader(
                        sensor_id=sensor_id,
                        port=sensor_info.port,
                        baudrate=sensor_info.baud,
                    ))
                    # Store task for later cleanup if needed
                    if not hasattr(self, 'sensor_tasks_map'):
                        self.sensor_tasks_map = {}
                    self.sensor_tasks_map[sensor_id] = task
                    return True
                else:
                    # Only log warning on first failure, not on every retry
                    was_failing = reconnection_failure_state.get(sensor_id, False)
                    if not was_failing:
                        logger.warning(f"✗ Could not re-detect {sensor_id.name}")
                        reconnection_failure_state[sensor_id] = True
                    
                    # Remove old port from used_ports if the sensor was assigned to one
                    # This allows the port to be reassigned to another sensor
                    if old_port and old_port in port_detector.used_ports:
                        port_detector.used_ports.discard(old_port)
                        logger.debug(f"Released port {old_port} from {sensor_id.name} for reuse")
                    return False
            
            # Periodic detection of missing sensors
            async def periodic_sensor_detection():
                """Periodically attempt to detect missing sensors with increasing wait times."""
                wait_time = 1  # Start with 1 second
                max_wait_time = 10
                last_detected_sensor = None  # Track last detected sensor to prioritize next detection
                
                while self.running:
                    try:
                        await asyncio.sleep(wait_time)
                        
                        # Find missing sensors
                        missing = set(sensor_bauds.keys()) - set(detected_sensor_info.keys())
                        
                        if missing:
                            # Try to detect ONE missing sensor at a time (not all at once)
                            # Prioritize the one after the last detected one (round-robin)
                            missing_list = sorted(missing)  # Sort for deterministic order
                            
                            # Find the next sensor to probe (after the last one we detected)
                            if last_detected_sensor:
                                try:
                                    idx = missing_list.index(last_detected_sensor) + 1
                                    if idx >= len(missing_list):
                                        idx = 0
                                except ValueError:
                                    idx = 0
                            else:
                                idx = 0
                            
                            sensor_to_detect = missing_list[idx]
                            last_detected_sensor = sensor_to_detect
                            
                            # Try to detect just this one sensor
                            newly_detected = port_detector.auto_detect_sensors(
                                {sensor_to_detect: sensor_bauds[sensor_to_detect]},
                                sensor_configs=config_loader.get_all_sensors(),
                                verbose=False
                            )
                            
                            if sensor_to_detect in newly_detected:
                                sensor_info = newly_detected[sensor_to_detect]
                                detected_sensor_info[sensor_to_detect] = (sensor_info.port, sensor_info.baud)
                                
                                # Log state change
                                logger.info(f"✓ Detected missing sensor {sensor_to_detect} on {sensor_info.port} @ {sensor_info.baud} baud")
                                missing_sensors_state[sensor_to_detect] = False
                                
                                # Add to health monitoring
                                sensor_reconnection_manager.add_sensor(sensor_to_detect, max_silence_time=5.0)
                                
                                # Register reconnection callback
                                sensor_reconnection_manager.register_reconnection_callback(sensor_to_detect, reconnect_sensor)
                                
                                # Start serial reader
                                task = loop.create_task(serial_reader(
                                    sensor_id=sensor_to_detect,
                                    port=sensor_info.port,
                                    baudrate=sensor_info.baud,
                                ))
                                if not hasattr(self, 'sensor_tasks_map'):
                                    self.sensor_tasks_map = {}
                                self.sensor_tasks_map[sensor_to_detect] = task
                                
                                # Reset wait time when a sensor is detected
                                wait_time = 1
                            else:
                                # Sensor not detected, it may not be connected yet
                                was_missing = missing_sensors_state.get(sensor_to_detect, True)
                                if not was_missing:
                                    logger.warning(f"✗ Lost sensor {sensor_to_detect} (not detected)")
                                    missing_sensors_state[sensor_to_detect] = True
                                    wait_time = 1
                        else:
                            # No missing sensors, can increase wait time
                            if wait_time < max_wait_time:
                                wait_time = min(wait_time + 1, max_wait_time)
                    
                    except Exception as e:
                        logger.debug(f"Error during periodic sensor detection: {e}")
            
            # Start health monitoring
            monitor_task = loop.create_task(sensor_reconnection_manager.start_monitoring())
            self.monitor_task = monitor_task
            
            # Auto-detect sensors initially
            logger.info("Detecting connected sensors...")
            detected_sensors = port_detector.auto_detect_sensors(
                sensor_bauds,
                sensor_configs=config_loader.get_all_sensors()
            )
            
            # Track initial missing sensors
            for sensor_id in sensor_bauds.keys():
                missing_sensors_state[sensor_id] = sensor_id not in detected_sensors
            
            if not detected_sensors:
                logger.warning("No sensors detected initially. Waiting for connections...")
            else:
                # Start serial readers for all detected sensors
                self.serial_tasks = []
                if not hasattr(self, 'sensor_tasks_map'):
                    self.sensor_tasks_map = {}
                
                for sensor_id, sensor_info in detected_sensors.items():
                    logger.info(f"Starting serial reader for {sensor_id}: {sensor_info.port} @ {sensor_info.baud} baud")
                    detected_sensor_info[sensor_id] = (sensor_info.port, sensor_info.baud)
                    
                    # Add to health monitoring only if detected
                    sensor_reconnection_manager.add_sensor(sensor_id, max_silence_time=5.0)
                    
                    # Register reconnection callback
                    sensor_reconnection_manager.register_reconnection_callback(sensor_id, reconnect_sensor)
                    
                    task = loop.create_task(serial_reader(
                        sensor_id=sensor_id,
                        port=sensor_info.port,
                        baudrate=sensor_info.baud,
                    ))
                    self.serial_tasks.append(task)
                    self.sensor_tasks_map[sensor_id] = task
            
            # Start periodic sensor detection task
            self.running = True
            detection_task = loop.create_task(periodic_sensor_detection())
            self.detection_task = detection_task
        
        # Test Manager
        # Already initialized as singleton
        
        logger.info("Background services started.")

    def stop_services(self):
        """Stop background services."""
            
        self.running = False
        
        sensor_manager.stop()
        
        # Stop health monitoring
        asyncio.create_task(sensor_reconnection_manager.stop_monitoring())
        
        if hasattr(self, 'detection_task'):
            self.detection_task.cancel()
        
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
