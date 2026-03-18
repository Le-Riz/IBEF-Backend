import asyncio
import logging
import queue
import threading
import time
from typing import Optional, Callable, Awaitable
import serial
from core.models.sensor_enum import SensorId
from core.sensor_reconnection import SensorHealthMonitor, SensorTask, SensorState

def make_serial_read_func(
    sensor_id: SensorId,
    port: str,
    baudrate: int = 9600,
    monitor=None,
    serial_timeout: float = 0.5,
) -> Callable[[], Awaitable[Optional[tuple[str, float]]]]:
    """
    Returns an async function that reads one line from the serial port for the sensor.
    The function returns the line if data is received, or None if not.
    Automatically closes and reopens the port on error to recover from I/O errors.
    Logs only once on disconnect and once on reconnect.
    Updates the SensorHealthMonitor state directly.
    """
    logger = logging.getLogger(__name__)

    line_queue: queue.Queue[tuple[str, float]] = queue.Queue(maxsize=1024)
    stop_event = threading.Event()
    reader_thread: Optional[threading.Thread] = None
    connected = False

    def _set_disconnected(error: Exception):
        nonlocal connected
        if connected:
            logger.warning(f"[Serial] {sensor_id} disconnected from {port}: {error}")
            connected = False
            if monitor is not None:
                monitor.state = SensorState.DISCONNECTED

    def _reader_loop():
        nonlocal connected
        ser = None
        while not stop_event.is_set():
            try:
                if ser is None:
                    ser = serial.Serial(port, baudrate, timeout=serial_timeout)
                    if not connected:
                        logger.warning(f"[Serial] {sensor_id} connected on {port} @ {baudrate} baud")
                        connected = True
                        if monitor is not None:
                            monitor.state = SensorState.CONNECTED
                            monitor.record_data()

                raw_line = ser.readline()
                if not raw_line:
                    continue

                try:
                    line = raw_line.decode("utf-8").strip()
                except UnicodeDecodeError:
                    logger.warning(f"Error decoding serial data from {sensor_id} ({port})")
                    continue

                if not line:
                    continue

                try:
                    line_queue.put_nowait((line, time.time()))
                except queue.Full:
                    # If the queue is full, discard the oldest line to make room for new data
                    line_queue.get_nowait()
                    line_queue.put_nowait((line, time.time()))

            except (serial.SerialException, OSError) as e:
                _set_disconnected(e)
                if ser is not None:
                    try:
                        ser.close()
                    except Exception:
                        pass
                    ser = None
                stop_event.wait(1.0)
            except Exception as e:
                _set_disconnected(e)
                if ser is not None:
                    try:
                        ser.close()
                    except Exception:
                        pass
                    ser = None
                stop_event.wait(1.0)

        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass

    def _ensure_reader_started():
        nonlocal reader_thread
        if reader_thread is None or not reader_thread.is_alive():
            stop_event.clear()
            reader_thread = threading.Thread(target=_reader_loop, daemon=True)
            reader_thread.start()

    def _close_reader():
        stop_event.set()
        if reader_thread is not None and reader_thread.is_alive():
            reader_thread.join(timeout=2.0)

    async def read_func() -> Optional[tuple[str, float]]:
        _ensure_reader_started()
        try:
            (line, timestamp) = line_queue.get()
            if monitor is not None:
                monitor.record_data()
            return (line, timestamp)
        except queue.Empty:
            return None

    # Close hook used by SensorTask.stop() to force-stop the reader thread.
    setattr(read_func, "close", _close_reader)

    return read_func

# Factory to create a SensorTask for a serial sensor
def create_serial_sensor_task(
    sensor_id: SensorId,
    port: str,
    baudrate: int = 9600,
    max_silence_time: float = 5.0,
    serial_timeout: float = 0.5,
) -> SensorTask:
    monitor = SensorHealthMonitor(sensor_id, max_silence_time=max_silence_time)
    read_func = make_serial_read_func(sensor_id, port, baudrate, monitor=monitor, serial_timeout=serial_timeout)
    return SensorTask(sensor_id, read_func, max_silence_time=max_silence_time, monitor=monitor)