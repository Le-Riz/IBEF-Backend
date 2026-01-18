# Sensor Configuration Guide

## Overview

The `sensors_config.json` file defines sensor types and their communication parameters. **Ports are automatically detected** - you do not need to configure them manually.

## Configuration File Structure

```json
{
  "emulation": true,
  "sensors": {
    "SENSOR_NAME": {
      "baud": 115200,
      "description": "Sensor description"
    }
  }
}
```

### Fields

#### Root Level

- **`emulation`** (boolean):
  - `true`: Run in simulation mode (no hardware required)
  - `false`: Run in hardware mode (auto-detects connected sensors)

#### Sensor Configuration

- **`baud`** (integer): Expected baud rate for serial communication
  - Default for motion sensors: `9600`
  - Default for force sensor: `115200`
  - Common alternatives: 4800, 19200, 38400, 57600
- **`description`** (string): Optional description of the sensor
- **Note**: Ports are NOT configured here - they are auto-detected on startup

## Current Setup

### Baud Rates

- **Motion Sensors (DISP_1, DISP_2, DISP_3, DISP_4, DISP_5)**: 9600 baud
- **Force Sensor**: 115200 baud

### Sensors

1. **FORCE**: Force measurement sensor (115200 baud)
2. **DISP_1**: Motion sensor 1 (9600 baud)
3. **DISP_2**: Motion sensor 2 (9600 baud)
4. **DISP_3**: Motion sensor 3 (9600 baud)
5. **DISP_4**: Motion sensor 4 (9600 baud)
6. **DISP_5**: Motion sensor 5 (9600 baud)

*Note: ARC is calculated from DISP values and does not require its own serial configuration.*

## How Auto-Detection Works

When you run in **hardware mode** (`emulation: false`):

1. Application lists all available serial ports
2. For each port, it tries to connect with each sensor's configured baud rate
3. It analyzes the incoming data to identify which sensor is on that port
4. Creates a mapping of sensors to their ports and bauds
5. Starts serial readers for each detected sensor

**Result**: No manual port configuration needed. Just plug in your sensors.

## Sensor Identification

The application recognizes sensors by their message format:

### FORCE Sensor

- Format: `ASC2` followed by numeric values
- Example: `ASC2 20945595 -165341 -1.527986e-01 -4.965955e+01 -0.000000e+00`
- Baud: 115200

### Motion Sensors (DISP)

- Format: Contains `SPC_VAL`, `usSenderId=`, and `Val=`
- Example: `76 144 262 us SPC_VAL usSenderId=0x2E01 ulMicros=76071216 Val=0.000`
- Baud: 9600

## Troubleshooting

### Sensor Not Detected

**Problem**: Application starts but doesn't find your sensor.

**Solutions**:

1. Check physical USB connection.
2. List available ports:

   ```bash
   # Linux/Mac
   ls /dev/tty*

   # Windows
   # Open Device Manager, check Ports (COM & LPT)
   ```

3. Check application logs for detection attempts.
4. Try different USB port on computer.

### Sensor Sending Garbage Data

**Problem**: Sensor detected but reading strange values.

**Root Cause**: Usually wrong baud rate.

**Solution**:

1. Check what baud rate the application is using (check logs).
2. Try different bauds in `sensors_config.json`:

   ```json
   "DISP_1": {
     "baud": 19200,
     "description": "Motion sensor - alternative baud"
   }
   ```

3. Common bauds to try: 4800, 9600, 19200, 38400, 115200.

### Detection With Wrong Baud (Warning)

**Message**: `⚠ Detected DISP_1 on /dev/ttyUSB0 @ 115200 baud (expected 9600)`

This means:

- Sensor was recognized on that port.
- But baud rate is different from configured.
- Update config if the detected baud is correct.

## Environment Variables

Override emulation mode without editing config file:

```bash
# Run in hardware mode
EMULATION_MODE=false hatch run python -m src.main

# Run in emulation mode
EMULATION_MODE=true hatch run python -m src.main
```

If `EMULATION_MODE` is not set, the value from `sensors_config.json` is used.

## Example Configurations

### Minimal Setup (Only FORCE)

```json
{
  "emulation": false,
  "sensors": {
    "FORCE": {
      "baud": 115200,
      "description": "Force sensor"
    }
  }
}
```

### Full Setup (All Sensors)

```json
{
  "emulation": false,
  "sensors": {
    "FORCE": {
      "baud": 115200,
      "description": "Force measurement sensor"
    },
    "DISP_1": {
      "baud": 9600,
      "description": "Motion sensor 1"
    },
    "DISP_2": {
      "baud": 9600,
      "description": "Motion sensor 2"
    },
    "DISP_3": {
      "baud": 9600,
      "description": "Motion sensor 3"
    },
    "DISP_4": {
      "baud": 9600,
      "description": "Motion sensor 4"
    },
    "DISP_5": {
      "baud": 9600,
      "description": "Motion sensor 5"
    }
  }
}
```

### Custom Baud Rates (Troubleshooting)

