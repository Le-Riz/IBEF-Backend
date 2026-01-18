# Sensor Connection Management

## Overview

The IBEF Backend includes an automatic sensor reconnection system that handles sensors being physically disconnected/reconnected during operation. When a sensor loses connection, the system automatically detects this and attempts to reconnect using an exponential backoff strategy.

## Connection States

Each sensor can be in one of four states:

- **`connected`** - Sensor is actively communicating and sending data
- **`disconnected`** - Sensor stopped sending data for more than 5 seconds
- **`reconnecting`** - System is attempting to reconnect the sensor
- **`failed`** - Sensor has failed permanently (after max reconnection attempts)

## How It Works

### Detection
The system monitors silence from each sensor. If a sensor doesn't send any data for **5 seconds**, it's marked as disconnected.

### Automatic Reconnection
When a disconnection is detected, the system attempts to reconnect using an **exponential backoff** strategy:

- **Initial delay**: 1.0 second
- **Multiplier**: 1.5x per attempt
- **Maximum delay**: 30.0 seconds (capped)

Example backoff progression:
```
Attempt 1: Wait 1.0s
Attempt 2: Wait 1.5s
Attempt 3: Wait 2.25s
Attempt 4: Wait 3.375s
...
Attempt N: Wait 30.0s (capped)
```

This exponential backoff prevents CPU overload from rapid reconnection attempts while maintaining responsiveness for sensors that quickly reconnect (like USB replug scenarios).

## Data Request Errors

When requesting data from a disconnected sensor, the API returns a **503 Service Unavailable** error.

### Error Response

**Status Code**: `503 Service Unavailable`

**Response Body:**

```json
{
  "detail": "Sensor FORCE is not connected"
}
```

### Affected Endpoints

All endpoints that retrieve sensor data return 503 if the requested sensor is not connected:

- `GET /api/sensor/{sensor_id}/data` - Latest calibrated data
- `GET /api/sensor/{sensor_id}/raw` - Latest raw data
- `GET /api/sensor/{sensor_id}/data/history` - Historical data
- `GET /api/graph/{sensor_name}` - Graphique (PNG)
- `GET /api/graph/{sensor_name}/base64` - Graphique (base64)

### Example Error

```bash
$ curl http://localhost:8000/api/sensor/FORCE/data
{
  "detail": "Sensor FORCE is not connected"
}
```

HTTP Status: 503

## Graphique Special Cases

The graphique endpoints have additional connection requirements:

### DISP_1 Graphique

Requires:

- `FORCE` connected (Y-axis)
- `DISP_1` connected (X-axis)

### ARC Graphique

Requires:

- `FORCE` connected (Y-axis)
- `DISP_2` AND `DISP_3` connected (used to calculate ARC for X-axis; DISP_4/DISP_5 are extra channels not used for ARC)

If any required sensor is not connected, the graphique endpoint returns 503:

```bash
$ curl http://localhost:8000/api/graph/ARC
{
  "detail": "Sensors DISP_2 and DISP_3 are not connected (required for ARC calculation)"
}
```

HTTP Status: 503

## Client Handling Strategy

When building clients that consume this API:

### 1. Check Health Before Requesting Data
```python
import requests

# Check if sensor is connected
health = requests.get("http://localhost:8000/api/config/health/FORCE").json()
if health["state"] == "connected":
    data = requests.get("http://localhost:8000/api/sensor/FORCE/data").json()
else:
    print(f"Sensor disconnected, waiting to reconnect...")
```

### 2. Handle 503 Errors Gracefully
```python
try:
    response = requests.get("http://localhost:8000/api/sensor/FORCE/data")
    if response.status_code == 503:
        print("Sensor not connected, retrying in 2 seconds...")
        time.sleep(2)
except Exception as e:
    print(f"Error: {e}")
```

### 3. Implement Retry Logic
```python
import time

def get_sensor_data_with_retry(sensor_id, max_retries=5):
    for attempt in range(max_retries):
        response = requests.get(f"http://localhost:8000/api/sensor/{sensor_id}/data")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 503:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Sensor disconnected, waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        else:
            raise Exception(f"API Error: {response.status_code}")
    
    raise Exception("Max retries exceeded, sensor still not connected")
```

## Configuration

### Silence Detection Timeout

By default, sensors are considered disconnected after 5 seconds of no data. This is configured in `src/core/service_manager.py`:

```python
sensor_reconnection_manager.add_sensor(sensor_name, max_silence_time=5.0)
```

### Backoff Parameters

Exponential backoff parameters are defined in `src/core/sensor_reconnection.py`:

```python
@dataclass
class SensorHealthMonitor:
    initial_reconnect_delay: float = 1.0      # Start with 1 second
    max_reconnect_delay: float = 30.0         # Cap at 30 seconds
    backoff_multiplier: float = 1.5           # Multiply by 1.5x each attempt
```

To customize these values, modify the dataclass defaults or adjust the `add_sensor()` call in service_manager.py.

## Hardware Mode Only

Sensor reconnection and connection checking **only occurs in hardware mode**. When running in emulation mode (`emulation: true` in config), sensors are always considered connected regardless of actual data flow.

This allows testing of graphiques and data endpoints without physical hardware.

## Troubleshooting

### Sensor Keeps Reconnecting

If a sensor repeatedly enters the `reconnecting` state, check:

1. **Physical connection**: Ensure USB cable is properly connected
2. **Baud rate**: Verify the sensor's baud rate matches `config/sensors_config.json`
3. **Port availability**: Check if another process is using the serial port
4. **Hardware issue**: The sensor may be failing

### Cannot Get Data (Always 503)

Check if sensor state shows as `failed`, manual reconnection may be needed:

1. Physically disconnect and reconnect the sensor
2. Check hardware logs
3. Restart the backend application

### Backoff Delays Too Aggressive/Lenient

Modify the backoff parameters in `src/core/sensor_reconnection.py`:
- **Memory**: ~1KB per sensor for tracking state
- **CPU**: <0.1% for 4 sensors with typical disconnection patterns

---

See also: [Sensor Configuration](sensor-config.md) | [Auto-Detection](auto-sensor-detection.md)
