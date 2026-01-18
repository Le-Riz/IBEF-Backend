# Automatic Sensor Port Detection System

## Overview

The application now automatically detects connected sensors and maps them to their serial ports. This eliminates the need to manually configure ports in the configuration file.

**Important**: Auto-detection **ONLY runs in hardware mode** (`emulation: false`). In emulation mode, no sensor detection occurs.

## How It Works

### 1. Configuration File (sensors_config.json)

The configuration file now contains only:

- Sensor names (FORCE, DISP_1, DISP_2, DISP_3, DISP_4, DISP_5)
- Expected baud rates for each sensor type
- Descriptions

```json
{
  "emulation": true,
  "sensors": {
    "FORCE": {
      "baud": 115200,
      "description": "Force sensor (capteur de force)"
    },
    "DISP_1": {
      "baud": 9600,
      "description": "Motion sensor 1 (capteur de mouvement 1)"
    }
  }
}
```

### 2. Automatic Port Detection (port_detector.py)

**This only runs when `emulation: false`**

When the application starts in hardware mode, it:

1. **Lists all available serial ports**
   - Uses `serial.tools.list_ports` to find connected devices

2. **Probes each port with expected baud rates**
   - Tries each sensor's configured baud rate
   - Reads incoming data from the port

3. **Identifies sensors by message format**
   - **FORCE sensor**: Recognizes `ASC2` format with 5 numeric parts
   - **Motion sensors (DISP)**: Recognizes `SPC_VAL` format with `usSenderId` and `Val=`

4. **Falls back to alternative baud rates**
   - If no sensor detected with standard bauds, tries alternatives: 4800, 19200, 38400, 57600, 115200
   - Logs a warning when alternative baud is used (might be wrong!)

5. **Creates port-to-sensor mapping**
   - Stores detected sensors with their ports and baud rates
   - Confidence score indicates how certain the detection is

## Advantages

✅ **No manual port configuration** - Just plug in sensors, it works automatically
✅ **Supports sensor hotswapping** - Plug/unplug sensors without restarting
✅ **Detects wrong baud rates** - Can suggest alternative bauds if data looks corrupted
✅ **Multiple simultaneous connections** - Supports up to 3 DISP + 1 FORCE simultaneously
✅ **Handles disconnected sensors** - Simply logs a warning, continues with others
✅ **Zero overhead in emulation mode** - No serial operations when testing

## Emulation vs Hardware Mode

### Emulation Mode (`emulation: true`)

- **No serial port detection**
- **No hardware access**
- **No external dependencies**
- SensorManager generates simulated data
- Perfect for testing without hardware
- Useful for development and CI/CD

### Hardware Mode (`emulation: false`)

- **Automatic sensor detection**
- **Serial port scanning and identification**
- **Real sensor data reading**
- Requires physical sensors connected
- Logs all detection attempts and results
- Falls back to alternative bauds if needed

## Workflow During Application Startup

### In Emulation Mode (`emulation: true`)

```text
Application Starts
  ↓
Load configuration
  ↓
Initialize sensor manager in EMULATION mode
  ↓
SensorManager generates simulated data
  ↓
NO HARDWARE ACCESS - NO SERIAL PORT DETECTION
```

### In Hardware Mode (`emulation: false`)

```text
Application Starts
  ↓
Load configuration
  ↓
Initialize sensor manager in HARDWARE mode
  ↓
Load sensor baud rates from config
  ↓
List available serial ports
  ↓
For each port and each sensor:
  → Try expected baud rate
  → Read and analyze first few lines
  → Check if message format matches sensor type
  ↓
If not detected with standard bauds:
  → Try alternative baud rates (4800, 19200, 38400, 57600, 115200)
  → Log warning if found (might be wrong setting!)
  ↓
Create mapping: sensor_name → {port, baud}
  ↓
Start serial readers for each detected sensor
  ↓
Begin reading real data from hardware
```

## Identification Patterns

### FORCE Sensor

- Message format: `ASC2 20945595 -165341 -1.527986e-01 -4.965955e+01 -0.000000e+00`
- Pattern: "ASC2" followed by 5 space-separated numeric values
- Baud: 115200

### Motion Sensors (DISP)

- Message format: `76 144 262 us SPC_VAL usSenderId=0x2E01 ulMicros=76071216 Val=0.000`
- Pattern: Contains "SPC_VAL", "usSenderId=", and "Val="
- Baud: 9600

## Handling Issues

### Sensor Not Detected

1. Check that sensor is physically connected
2. Verify USB cable is functional
3. Check application logs for port detection attempts
4. Try different USB port on computer

### Sensor Detected But With Wrong Baud

Application will log:

```text
⚠ Detected DISP_1 on /dev/ttyUSB0 @ 115200 baud (expected 9600)
```

This means:

- Data format was recognized
- But baud rate is different from expected
- Update `sensors_config.json` if the alternative baud is correct

### Sensor Detected But Sending Garbage Data

Typical issue: Sensor on correct port but wrong baud rate

- Check baud rate in `sensors_config.json`
- Try alternative bauds:
  - Motion sensors: usually 9600, sometimes 4800, 19200
  - Force sensor: usually 115200, sometimes 9600, 38400

### Multiple Sensors Confused on Same Port

Each sensor should have unique `usSenderId` (for motion sensors) or be identified by format.

If sensors are getting mixed up:

1. Test each sensor individually (disconnect others)
2. Check their message formats
3. Verify they're on different ports

## Configuration Examples

### Only Use DISP_1

```json
{
  "emulation": false,
  "sensors": {
    "FORCE": {"baud": 115200, "description": "Force sensor"},
    "DISP_1": {"baud": 9600, "description": "Motion sensor 1"}
  }
}
```

### Try Alternative Baud for Problematic DISP

```json
{
  "sensors": {
    "DISP_1": {"baud": 19200, "description": "Motion sensor with alternative baud"}
  }
}
```

## Environment Variables

```bash
# Force hardware mode (auto-detection)
EMULATION_MODE=false python -m src.main

# Force emulation mode (skip detection)
EMULATION_MODE=true python -m src.main
```

## Debugging Auto-Detection

Enable debug logging to see detection process:

The system logs:

- Available ports found
- Detection attempts for each port/baud combination
- Detected sensors with confidence scores
- Alternative baud attempts and warnings

## Technical Implementation

### Port Detector Class

- **File**: `src/core/port_detector.py`
- **Type**: Singleton pattern
- **Methods**:
  - `auto_detect_sensors(sensor_bauds)` - Main detection method
  - `probe_sensor(port, baud, timeout)` - Test single port
  - `_identify_sensor_from_line(line)` - Parse message format
  - `get_all_detected()` - Get detection results

### Integration Points

- **ServiceManager** (`src/core/service_manager.py`): Calls `port_detector.auto_detect_sensors()` at startup
- **ConfigLoader** (`src/core/config_loader.py`): Provides sensor baud configurations
- **SerialHandler** (`src/core/services/serial_handler.py`): Receives port and baud from detection results

## Test Coverage

12 tests for port detection:

- ✅ FORCE sensor identification
- ✅ Motion sensor identification
- ✅ Unknown format handling
- ✅ Partial format rejection
- ✅ Port availability checking
- ✅ Singleton pattern validation
- ✅ Configuration API integration

See `tests/test_port_detector.py` for details.

## Future Enhancements

Possible improvements:

1. **API endpoint** to expose detected sensors
2. **Persistence** of detected mappings (cache for faster startup)
3. **Sensor verification** - ping each sensor periodically
4. **Re-detection** - automatic detection when new sensor appears
5. **Baud rate suggestions** - when data is garbled, try alternatives automatically
