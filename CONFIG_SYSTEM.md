# Configuration System Implementation Summary

## What Was Added

A complete JSON-based configuration system for managing sensor settings has been implemented with the following components:

### 1. Configuration File: `config/sensors_config.json`

- **Location**: `config/sensors_config.json` at the project root
- **Structure**:
  - Global `emulation` mode setting
  - Per-sensor configuration with baud rate, port, and enabled status
- **Sensors Configured**:
  - FORCE: 115200 baud (force sensor)
  - DISP_1, DISP_2, DISP_3: 9600 baud (motion sensors)
  - ARC: 9600 baud (arc/deflection sensor)

### 2. Configuration Loader: `src/core/config_loader.py`

A singleton class providing methods to:

- Load configuration from JSON file
- Get sensor configurations by name
- Get baud rates and ports for specific sensors
- Check if sensors are enabled
- Filter only enabled sensors
- Reload configuration at runtime

Key methods:

- `get_emulation_mode()` - Get emulation mode setting
- `get_sensor_config(sensor_name)` - Get specific sensor config
- `get_sensor_baud(sensor_name)` - Get baud rate (defaults: 9600 or 115200)
- `get_sensor_port(sensor_name)` - Get serial port
- `is_sensor_enabled(sensor_name)` - Check if sensor is active
- `get_enabled_sensors()` - Get only enabled sensors

### 3. Configuration API Endpoints: `src/routers/config.py`

RESTful API to access configuration:

- `GET /api/config` - Full configuration
- `GET /api/config/emulation` - Emulation mode setting
- `GET /api/config/sensors` - All sensor configurations
- `GET /api/config/sensors/enabled` - Only enabled sensors
- `GET /api/config/sensors/{sensor_name}` - Specific sensor config

### 4. Integration Changes

#### `src/main.py`

- Loads emulation mode from configuration file
- Environment variable `EMULATION_MODE` overrides config file

#### `src/core/service_manager.py`

- Modified to start serial readers for all enabled sensors
- Uses configuration for port and baud rate per sensor
- Supports multiple simultaneous serial connections

#### `src/core/services/serial_handler.py`

- Added optional `sensor_name` parameter for better logging
- Displays baud rate in connection messages

### 5. Tests

#### `tests/test_config_loader.py` (10 tests)

- Config loading and structure validation
- Sensor configuration access
- Baud rate defaults (115200 for FORCE, 9600 for motion)
- Enabled/disabled sensor filtering
- Port retrieval
- Singleton pattern validation

#### `tests/test_config_api.py` (7 tests)

- Full configuration endpoint
- Emulation mode endpoint
- All sensors endpoint
- Enabled sensors endpoint
- Specific sensor endpoints
- Error handling (404 for invalid sensors)

### 6. Documentation: `docs/sensor-config.md`

Complete guide covering:

- Configuration file structure and fields
- Baud rate defaults
- Troubleshooting guide for weird sensor values
- Serial port identification procedure
- API endpoint reference
- Environment variable usage

## Key Features

✅ **Flexible Sensor Mapping**: Easily reassign sensors to different ports
✅ **Baud Rate Configuration**: Different rates for different sensors (115200 for force, 9600 for motion)
✅ **Enable/Disable Sensors**: Without editing code, control which sensors initialize
✅ **Multiple Simultaneous Connections**: Support for multiple serial ports at different baud rates
✅ **Emulation Mode Toggle**: Switch between hardware and simulation mode via config
✅ **Environment Variable Override**: Set `EMULATION_MODE` to override config file
✅ **Runtime Reloadable**: `reload_config()` method for dynamic updates
✅ **REST API Access**: Query configuration via API endpoints
✅ **Comprehensive Tests**: 17 new tests covering all functionality
✅ **Full Documentation**: Guide for configuration and troubleshooting

## Usage Examples

### Edit Configuration

```bash
# Edit config/sensors_config.json
{
  "emulation": false,
  "sensors": {
    "FORCE": {
      "baud": 115200,
      "port": "/dev/ttyUSB0",
      "enabled": true
    },
    "DISP_1": {
      "baud": 9600,
      "port": "/dev/ttyUSB1",
      "enabled": true
    }
  }
}
```

### Check via API

```bash
# Get all sensors
curl http://localhost:8000/api/config/sensors

# Get FORCE sensor config
curl http://localhost:8000/api/config/sensors/FORCE

# Get only enabled sensors
curl http://localhost:8000/api/config/sensors/enabled
```

### Override via Environment

```bash
# Run in hardware mode (override config file)
EMULATION_MODE=false python -m src.main

# Run in emulation mode
EMULATION_MODE=true python -m src.main
```

### Troubleshooting Sensor Values

If a sensor reads bizarre values:

1. Check baud rate in config
2. Try different baud rates (common: 9600, 19200, 38400, 115200)
3. Verify correct port assignment

Example: Try 115200 for a motion sensor

```json
"DISP_1": {
  "baud": 115200,
  "port": "/dev/ttyUSB0",
  "enabled": true
}
```

## Test Results

- **Total tests**: 108 (up from 91)
- **New tests**: 17
  - 10 config loader tests
  - 7 config API tests
- **All tests passing**: ✅ 108/108

## Files Added

- `config/sensors_config.json` - Configuration file
- `src/core/config_loader.py` - Configuration loader module
- `src/routers/config.py` - Configuration API endpoints
- `tests/test_config_loader.py` - Configuration loader tests
- `tests/test_config_api.py` - Configuration API tests
- `docs/sensor-config.md` - Configuration documentation

## Files Modified

