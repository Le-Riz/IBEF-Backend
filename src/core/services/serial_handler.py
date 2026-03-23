import asyncio
import logging
import time
import platform
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
    def __init__(self, 
        sensor_id: SensorId,
        port: str,
        queue: asyncio.Queue[tuple[SensorId, str, float]],
        baudrate: int = 9600,
        serial_timeout: float = 0.01,
    ):
        
        self.baudrate = baudrate
        self.port = port
        self.timeout = serial_timeout
        self.serial = None
        self.sensor_id = sensor_id
        self.queue = queue
        self.running = False
        
    def start(self):
        """Start the serial handler by launching the read loop in an asynchronous task."""
        self.running = True
        asyncio.create_task(self.read_serial())
    
    def stop(self):
        """Stop the serial handler and close the serial port if open."""
        self.running = False
        if self.serial and self.serial.is_open:
            self.serial.close()
    
    async def read_serial(self):
        """Continuously read from the serial port, handle reconnections, and put data into the queue."""
        while self.running:
            try:
                if self.serial is None:
                    try:
                        self.serial = await asyncio.to_thread(
                            serial.Serial, port=self.port, baudrate=self.baudrate, timeout=self.timeout
                        )
                        logger.info(f"SerialHandler for {self.sensor_id.name} reconnected to {self.port} at {self.baudrate} baud.")
                        
                        # Apply platform-specific optimizations
                        if platform.system() == "Linux":
                            optimize_linux_serial(self.serial)
                        
                    except Exception as e:
                        logger.error(f"Failed to reconnect SerialHandler for {self.sensor_id.name} on {self.port}: {e}")
                        await asyncio.sleep(0.5)
                        continue
                
                line = await asyncio.to_thread(self.serial.readline)
                if line:
                    timestamp = time.time()
                    
                    decoded_line = line.decode('utf-8', errors='ignore').strip()
                    
                    if decoded_line:
                        if self.queue.full():
                            try:
                                self.queue.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
                        await self.queue.put((self.sensor_id, decoded_line, timestamp))
                    
            except Exception as e:
                logger.error(f"Error reading from serial port for {self.sensor_id}: {e}")
                if self.serial:
                    try:
                        self.serial.close()
                    except Exception as close_error:
                        logger.error(f"Error closing serial port for {self.sensor_id}: {close_error}")
                    self.serial = None
                await asyncio.sleep(1.0)