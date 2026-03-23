import logging
import queue
import time
import platform
import threading
import serial
from core.models.sensor_enum import SensorId

logger = logging.getLogger(__name__)


def optimize_linux_serial(ser):
    """Linux-specific optimizations for low-latency serial communication"""
    
    optimizations = []
    
    # 1. Set low latency mode
    try:
        import fcntl
        import termios
        
        # Get file descriptor
        fd = ser.fileno()
        
        # Set low latency flag
        attrs = termios.tcgetattr(fd)
        attrs[6][termios.VMIN] = 1      # Minimum characters to read
        attrs[6][termios.VTIME] = 0     # Timeout in deciseconds
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        
        optimizations.append("Low latency mode")
        
    except (ImportError, AttributeError, OSError) as e:
        logger.debug(f"Could not set low latency mode: {e}")
    
    # 2. Disable exclusive access for performance
    try:
        ser.exclusive = False
        optimizations.append("Exclusive access disabled")
    except AttributeError:
        logger.debug("Serial port does not support exclusive mode setting")
    
    # 3. Set large buffer sizes
    try:
        ser.set_buffer_size(rx_size=16384, tx_size=8192)
        optimizations.append("Large buffers (16KB RX, 8KB TX)")
    except AttributeError:
        logger.debug("Serial port does not support buffer size configuration")
    
    if optimizations:
        logger.info(f"Applied Linux optimizations: {', '.join(optimizations)}")
    
    return optimizations


def check_linux_serial_limits():
    """Check Linux system limits that affect serial performance"""
    
    checks = {}
    
    try:
        # Check USB buffer sizes
        with open('/sys/module/usbcore/parameters/usbfs_memory_mb', 'r') as f:
            usb_memory = int(f.read().strip())
            checks['usb_memory'] = f"{usb_memory} MB"
            
            if usb_memory < 64:
                logger.warning("USB memory buffer is low. Consider increasing it: "
                             "echo 64 > /sys/module/usbcore/parameters/usbfs_memory_mb")
    
    except FileNotFoundError:
        checks['usb_memory'] = "Not available"
    
    return checks


class SerialHandler:
    """
    Dedicated blocking-thread serial reader.
    
    Each instance runs its own daemon thread that blocks on serial.readline().
    Decoded lines are pushed into a thread-safe queue.Queue as
    (SensorId, decoded_line, timestamp) tuples.
    """

    def __init__(self, 
        sensor_id: SensorId,
        port: str,
        queue: queue.Queue,
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
        self._drop_count = 0
        self._thread: threading.Thread | None = None
        
    def start(self):
        """Start the dedicated reader thread."""
        self.running = True
        self._thread = threading.Thread(
            target=self._read_loop,
            daemon=True,
            name=f"SerialReader-{self.sensor_id.name}",
        )
        self._thread.start()
    
    def stop(self):
        """Signal the thread to stop and wait for it to exit."""
        self.running = False
        if self.serial and self.serial.is_open:
            self.serial.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._drop_count > 0:
            logger.warning(f"SerialHandler {self.sensor_id.name}: total dropped frames = {self._drop_count}")
    
    def _read_loop(self):
        """
        Blocking read loop (runs in its own thread).
        
        Connects to the serial port, reads lines, timestamps them,
        and pushes them into the shared queue.
        """
        while self.running:
            try:
                # Connect / reconnect
                if self.serial is None:
                    try:
                        self.serial = serial.Serial(
                            port=self.port,
                            baudrate=self.baudrate,
                            timeout=self.timeout,
                        )
                        logger.info(
                            f"SerialHandler for {self.sensor_id.name} connected "
                            f"to {self.port} at {self.baudrate} baud."
                        )
                        
                        if platform.system() == "Linux":
                            optimize_linux_serial(self.serial)
                        
                    except Exception as e:
                        logger.error(
                            f"Failed to connect SerialHandler for "
                            f"{self.sensor_id.name} on {self.port}: {e}"
                        )
                        time.sleep(0.5)
                        continue
                
                # Blocking read — waits up to self.timeout for a full line
                line = self.serial.readline()
                if line:
                    timestamp = time.time()
                    decoded_line = line.decode('utf-8', errors='ignore').strip()
                    
                    if decoded_line:
                        # Drop oldest if queue is full
                        if self.queue.full():
                            try:
                                self.queue.get_nowait()
                                self._drop_count += 1
                                if self._drop_count % 100 == 1:
                                    logger.warning(
                                        f"{self.sensor_id.name}: dropped "
                                        f"{self._drop_count} frames (queue full)"
                                    )
                            except queue.Empty:
                                pass
                        self.queue.put_nowait(
                            (self.sensor_id, decoded_line, timestamp)
                        )
                    
            except Exception as e:
                logger.error(f"Error reading serial port for {self.sensor_id.name}: {e}")
                if self.serial:
                    try:
                        self.serial.close()
                    except Exception as close_error:
                        logger.error(f"Error closing serial port for {self.sensor_id.name}: {close_error}")
                    self.serial = None
                time.sleep(1.0)