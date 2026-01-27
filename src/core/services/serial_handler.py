
import asyncio
from typing import Optional, Callable
import serial
from core.event_hub import event_hub
from core.models.sensor_enum import SensorId
from core.sensor_reconnection import SensorTask
from core.sensor_reconnection import SensorHealthMonitor, SensorTask, SensorState

from typing import Awaitable

def make_serial_read_func(sensor_id: SensorId, port: str, baudrate: int = 9600, monitor=None) -> Callable[[], Awaitable[Optional[str]]]:
    """
    Returns an async function that reads one line from the serial port for the sensor.
    The function returns the line if data is received, or None if not.
    Automatically closes and reopens the port on error to recover from I/O errors.
    Logs only once on disconnect and once on reconnect.
    Updates the SensorHealthMonitor state directly.
    """
    import logging
    logger = logging.getLogger(__name__)
    ser = None
    connected = False
    async def read_func():
        nonlocal ser, connected
        try:
            if ser is None:
                ser = serial.Serial(port, baudrate, timeout=0.1)
                if not connected:
                    logger.warning(f"[Serial] {sensor_id} connected on {port} @ {baudrate} baud")
                    connected = True
                    if monitor is not None:
                        monitor.state = SensorState.CONNECTED
                        monitor.record_data()
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        event_hub.send_all_on_topic("serial_data", (sensor_id, line))
                        if monitor is not None:
                            monitor.record_data()
                        return line
                except UnicodeDecodeError:
                    logger.warning(f"Error decoding serial data from {sensor_id} ({port})")
            await asyncio.sleep(0.01)
            return None
        except (serial.SerialException, OSError) as e:
            if connected:
                logger.warning(f"[Serial] {sensor_id} disconnected from {port}: {e}")
                connected = False
                if monitor is not None:
                    monitor.state = SensorState.DISCONNECTED
            if ser is not None:
                try:
                    ser.close()
                except Exception:
                    pass
                ser = None
            await asyncio.sleep(1.0)
            return None
        except Exception as e:
            if connected:
                logger.warning(f"[Serial] {sensor_id} disconnected from {port}: {e}")
                connected = False
                if monitor is not None:
                    monitor.state = SensorState.DISCONNECTED
            if ser is not None:
                try:
                    ser.close()
                except Exception:
                    pass
                ser = None
            await asyncio.sleep(1.0)
            return None
    return read_func

# Factory to create a SensorTask for a serial sensor
def create_serial_sensor_task(sensor_id: SensorId, port: str, baudrate: int = 9600, max_silence_time: float = 5.0) -> SensorTask:
    monitor = SensorHealthMonitor(sensor_id, max_silence_time=max_silence_time)
    read_func = make_serial_read_func(sensor_id, port, baudrate, monitor=monitor)
    return SensorTask(sensor_id, read_func, max_silence_time=max_silence_time, monitor=monitor)
