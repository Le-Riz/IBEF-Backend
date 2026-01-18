import asyncio
from typing import Optional
import serial
from core.event_hub import event_hub

async def serial_reader(port: str, baudrate: int = 9600, sensor_name: Optional[str] = None):
    """Read data from a serial port and publish it to the global event hub.
    
    Args:
        port (str): The serial port to connect to (e.g., "/dev/ttyUSB0" or "COM3").
        baudrate (int): The baud rate for the serial connection (default 9600).
        sensor_name (str): Optional sensor name for logging and identification.
    """
    sensor_label = f"{sensor_name} ({port})" if sensor_name else port
    print(f"Trying to connect to {sensor_label} at {baudrate} baud...")
    try:
        # Open the serial port
        ser = serial.Serial(port, baudrate, timeout=0.1)
        print(f"Connected to serial port: {sensor_label}")
        while True:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        event_hub.send_all_on_topic("serial_data", line)
                except UnicodeDecodeError:
                    print(f"Error decoding serial data from {sensor_label}")
            
            # Small pause to avoid blocking the event loop
            await asyncio.sleep(0.01)

    except serial.SerialException as e:
        print(f"Serial connection error on {sensor_label}: {e}")
    except Exception as e:
        print(f"Unexpected error in serial reader ({sensor_label}): {e}")
