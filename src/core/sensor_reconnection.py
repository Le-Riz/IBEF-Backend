import asyncio
import logging
import time
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from core.models.sensor_enum import SensorId

logger = logging.getLogger(__name__)


class SensorState(Enum):
    """Sensor connection states."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class SensorHealthMonitor:
    """Monitors and manages sensor connection health."""
    sensor_id: SensorId
    max_silence_time: float = 5.0  # Seconds without data before considering disconnected
    initial_reconnect_delay: float = 1.0  # Initial delay in seconds
    max_reconnect_delay: float = 30.0  # Maximum delay in seconds
    backoff_multiplier: float = 1.5  # Multiply delay by this factor each retry
    
    # State tracking
    last_data_time: float = field(default_factory=time.time)
    state: SensorState = SensorState.CONNECTED
    reconnect_attempts: int = 0
    current_backoff_delay: float = field(default=0.0)
    
    def __post_init__(self):
        self.current_backoff_delay = self.initial_reconnect_delay
        self.last_data_time = time.time()
    
    def record_data(self):
        """Record that data was received from this sensor."""
        self.last_data_time = time.time()
        if self.state != SensorState.CONNECTED:
            logger.info(f"✓ {self.sensor_id.name} reconnected!")
            self.state = SensorState.CONNECTED
            self.reconnect_attempts = 0
            self.current_backoff_delay = self.initial_reconnect_delay
    
    def check_silence(self) -> bool:
        """Check if sensor has been silent too long."""
        silence_duration = time.time() - self.last_data_time
        return silence_duration > self.max_silence_time
    
    def get_silence_duration(self) -> float:
        """Get how long sensor has been silent."""
        return time.time() - self.last_data_time
    
    def mark_disconnected(self):
        """Mark sensor as disconnected and prepare for reconnection."""
        if self.state != SensorState.DISCONNECTED:
            logger.warning(f"⚠ {self.sensor_id.name} disconnected (no data for {self.get_silence_duration():.1f}s)")
            self.state = SensorState.DISCONNECTED
            self.reconnect_attempts = 0
            self.current_backoff_delay = self.initial_reconnect_delay
    
    def mark_reconnecting(self):
        """Mark sensor as currently attempting reconnection."""
        self.state = SensorState.RECONNECTING
        self.reconnect_attempts += 1
        logger.info(f"🔄 Attempting to reconnect {self.sensor_id.name} (attempt {self.reconnect_attempts}, wait {self.current_backoff_delay:.1f}s)...")
    
    def mark_failed(self):
        """Mark reconnection attempt as failed."""
        self.state = SensorState.FAILED
    
    def get_next_retry_delay(self) -> float:
        """Get the delay for the next reconnection attempt with backoff."""
        delay = self.current_backoff_delay
        # Increase delay for next attempt, but cap at max
        self.current_backoff_delay = min(
            self.current_backoff_delay * self.backoff_multiplier,
            self.max_reconnect_delay
        )
        return delay
    
    def reset_backoff(self):
        """Reset backoff to initial value (when reconnected)."""
        self.current_backoff_delay = self.initial_reconnect_delay
        self.reconnect_attempts = 0


class SensorReconnectionManager:
    """Manages sensor health monitoring and automatic reconnection."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SensorReconnectionManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.monitors: Dict[SensorId, SensorHealthMonitor] = {}
        self.reconnection_callbacks: Dict[SensorId, Callable] = {}  # sensor_id -> callback
        self.reconnection_tasks: Dict[SensorId, asyncio.Task] = {}  # sensor_id -> task
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self.emulation_mode = True  # Start in emulation mode by default
    
    def add_sensor(self, sensor_id: SensorId, max_silence_time: float = 5.0, is_connected: bool = True):
        """Register a sensor for health monitoring.
        
        Args:
            sensor_id: SensorId enum value (e.g., SensorId.FORCE, SensorId.DISP_1)
            max_silence_time: Seconds of no data before marking disconnected
            is_connected: If True, initialize as CONNECTED; if False, as DISCONNECTED
        """
        monitor = SensorHealthMonitor(
            sensor_id=sensor_id,
            max_silence_time=max_silence_time
        )
        if is_connected:
            # Reset timestamp to now so sensor starts as connected
            monitor.last_data_time = time.time()
            monitor.state = SensorState.CONNECTED
        else:
            monitor.state = SensorState.DISCONNECTED
        
        self.monitors[sensor_id] = monitor
        status = "connected" if is_connected else "disconnected"
        logger.info(f"Added health monitor for {sensor_id.name} (max silence: {max_silence_time}s, initial: {status})")
    
    def register_reconnection_callback(self, sensor_id: SensorId, callback: Callable):
        """
        Register a callback function to attempt reconnection for a sensor.
        
        Callback should be async and accept sensor_name as parameter:
        async def reconnect(sensor_name: str) -> bool:
            # Try to reconnect
            # Return True if successful, False if failed
        """
        self.reconnection_callbacks[sensor_id] = callback
    
    def record_sensor_data(self, sensor_id: SensorId):
        """Record that data was received from a sensor."""
        if sensor_id in self.monitors:
            self.monitors[sensor_id].record_data()
    
    async def start_monitoring(self):
        """Start health monitoring loop."""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting sensor health monitoring...")
        
        try:
            while self._running:
                await self._monitor_tick()
                await asyncio.sleep(1.0)  # Check health every second
        except asyncio.CancelledError:
            logger.info("Sensor health monitoring stopped")
        except Exception as e:
            logger.error(f"Error in health monitoring: {e}")
        finally:
            self._running = False
    
    async def _monitor_tick(self):
        """Single monitoring cycle."""
        for sensor_id, monitor in self.monitors.items():
            # Check if sensor is silent
            if monitor.state == SensorState.CONNECTED and monitor.check_silence():
                monitor.mark_disconnected()
            
            # Handle disconnected sensors - start reconnection
            elif monitor.state == SensorState.DISCONNECTED:
                await self._start_reconnection(sensor_id)
            
            # Handle already reconnecting - check if task is done
            elif monitor.state == SensorState.RECONNECTING:
                if sensor_id in self.reconnection_tasks:
                    task = self.reconnection_tasks[sensor_id]
                    if task.done():
                        try:
                            success = task.result()
                            if success:
                                monitor.record_data()  # Will set state to CONNECTED
                                logger.info(f"✓ {sensor_id.name} successfully reconnected")
                            else:
                                monitor.mark_failed()
                        except Exception as e:
                            logger.error(f"Reconnection error for {sensor_id.name}: {e}")
                            monitor.mark_failed()
                        finally:
                            del self.reconnection_tasks[sensor_id]
            
            # Handle failed - retry with backoff
            elif monitor.state == SensorState.FAILED:
                await self._start_reconnection(sensor_id)
    
    async def _start_reconnection(self, sensor_id: SensorId):
        """Start a reconnection attempt for a sensor."""
        monitor = self.monitors[sensor_id]
        
        if sensor_id not in self.reconnection_callbacks:
            logger.warning(f"No reconnection callback registered for {sensor_id.name}")
            return
        
        # Get backoff delay
        delay = monitor.get_next_retry_delay()
        
        # Mark as reconnecting
        monitor.mark_reconnecting()
        
        # Create task to wait and then attempt reconnection
        async def reconnect_with_delay():
            await asyncio.sleep(delay)
            callback = self.reconnection_callbacks[sensor_id]
            try:
                success = await callback(sensor_id)
                return success
            except Exception as e:
                logger.error(f"Exception during reconnection of {sensor_id.name}: {e}")
                return False
        
        task = asyncio.create_task(reconnect_with_delay())
        self.reconnection_tasks[sensor_id] = task
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    def get_sensor_status(self, sensor_id: SensorId) -> Optional[SensorHealthMonitor]:
        """Get detailed status of a sensor."""
        if sensor_id not in self.monitors:
            return None
        
        return self.monitors[sensor_id]
    
    def get_all_statuses(self) -> Dict[SensorId, SensorHealthMonitor]:
        """Get status of all monitored sensors."""
        return {
            sensor_id: status
            for sensor_id in self.monitors.keys()
            if (status := self.get_sensor_status(sensor_id)) is not None
        }
    
    def is_sensor_connected(self, sensor_id: SensorId) -> bool:
        """Check if a sensor is currently connected.
        
        In emulation mode, sensors enabled=false sont considérés comme déconnectés.
        En hardware, on vérifie l'état réel.
        Pour ARC (calculé), on vérifie DISP_1, DISP_2, DISP_3.
        """
        from core.config_loader import config_loader
        if self.emulation_mode:
            # ARC dépend de ses capteurs réels
            if sensor_id == SensorId.ARC:
                return (
                    self.is_sensor_connected(SensorId.DISP_1) and
                    self.is_sensor_connected(SensorId.DISP_2) and
                    self.is_sensor_connected(SensorId.DISP_3)
                )
            # Pour les autres, enabled doit être True
            return config_loader.is_sensor_enabled(sensor_id)

        # Mode hardware : logique inchangée
        if sensor_id == SensorId.ARC:
            return (
                self.is_sensor_connected(SensorId.DISP_1) and
                self.is_sensor_connected(SensorId.DISP_2) and
                self.is_sensor_connected(SensorId.DISP_3)
            )
        if sensor_id not in self.monitors:
            return False
        return self.monitors[sensor_id].state == SensorState.CONNECTED


# Global singleton instance
sensor_reconnection_manager = SensorReconnectionManager()
