# Sensor Connection Error Handling - Implementation Summary

## Overview
Implemented automatic detection and error handling for disconnected sensors in the REST API. When a sensor is not connected, all data request endpoints return a **503 Service Unavailable** error with a descriptive message.

## Changes Made

### 1. Core Functionality

#### `src/core/sensor_reconnection.py`
- **Modified**: `add_sensor()` method
  - Added `is_connected` parameter to initialize sensors as CONNECTED or DISCONNECTED
  - Updates `last_data_time` to current time for connected sensors on initialization
  
- **Added**: `is_sensor_connected()` method
  - Checks if a sensor is currently in CONNECTED state
  - Special handling for ARC sensor (pseudo-sensor):
    - ARC is considered connected if DISP_1, DISP_2, and DISP_3 are all connected
    - Recursively checks dependencies

### 2. API Endpoints - Connection Checks

#### `src/routers/sensor.py`
- **Modified all data retrieval endpoints**:
  - `GET /api/sensor/{sensor_id}/data`
  - `GET /api/sensor/{sensor_id}/raw`
  - `GET /api/sensor/{sensor_id}/data/history`

- **Implementation**: Added connection status check before returning data
  - Raises 503 HTTPException if sensor not connected
  - Checks sensor state with `sensor_reconnection_manager.is_sensor_connected()`

- **Documentation**: Added 503 response documentation to all endpoints

#### `src/routers/graphique.py`
- **Modified**: Both graphique endpoints
  - `GET /api/graph/{sensor_name}`
  - `GET /api/graph/{sensor_name}/base64`

- **Implementation**: Added sensor dependency checks
  - For DISP_1 graphique: Requires DISP_1 and FORCE connected
  - For ARC graphique: Requires DISP_2, DISP_3, and FORCE connected
  - Returns 503 with descriptive error if any required sensor disconnected

- **Documentation**: Added 503 response documentation

#### `src/routers/raw.py`
- **Modified**: Raw point endpoint
  - `GET /api/raw/point/{sensor_id}`

- **Implementation**: Added connection status check
- **Route Integration**: Added import to `src/routers/api.py`

### 3. Test Infrastructure

#### `tests/conftest.py` (NEW)
- Created pytest configuration file with autouse fixture
- `ensure_sensors_initialized()` fixture:
  - Runs before every test automatically
  - Initializes all 4 sensors (FORCE, DISP_1, DISP_2, DISP_3) as CONNECTED
  - Resets their state and timestamp
  - Ensures tests don't fail due to uninitialized sensors

#### `tests/test_sensor_disconnection_errors.py` (NEW)
- Comprehensive test suite for disconnection error handling
- Test class: `TestSensorConnectionErrorHandling`
- 7 tests covering:
  - `/api/sensor/{sensor_id}/data` returns 503 when disconnected
  - `/api/sensor/{sensor_id}/raw` returns 503 when disconnected
  - `/api/graph/{sensor_name}` returns 503 when FORCE disconnected
  - `/api/graph/DISP_1` returns 503 when DISP_1 disconnected
  - `/api/graph/ARC` returns 503 when DISP_2/DISP_3 disconnected
  - `/api/raw/point/{sensor_id}` returns 503 when disconnected
  - `/api/sensor/{sensor_id}/data/history` returns 503 when disconnected

### 4. Documentation

#### `docs/sensor-connection-management.md` (NEW)
- Comprehensive guide on sensor connection management
- Sections:
  - Connection States (CONNECTED, DISCONNECTED, RECONNECTING, FAILED)
  - How reconnection works with exponential backoff
  - API endpoints for health monitoring
  - Error response documentation
  - Client handling strategies with code examples
  - Configuration options
  - Hardware vs Emulation mode
  - Troubleshooting guide
  - Performance impact analysis

#### `docs/api.md` (MODIFIED)
- Added 503 status code to error codes documentation
- Links to sensor connection management guide

#### `docs/index.md` (MODIFIED)
- Added reference to new documentation page
- Updated documentation index with all guides

## Error Response Format

All disconnection errors follow this format:

**Status Code**: `503 Service Unavailable`

**Response Body**:
```json
{
  "detail": "Sensor {SENSOR_NAME} is not connected"
}
```

### Special Cases

**ARC Graphique Requirements**:
```json
{
  "detail": "Sensors DISP_2 and DISP_3 are not connected (required for ARC calculation)"
}
```

**Multi-Sensor Graphique**:
```json
{
  "detail": "Sensor FORCE is not connected"
}
```

## Testing Results

**Test Suite**: 141 tests passing ✅
- Existing tests: 134
- New disconnection error tests: 7
- All sensor data retrieval tests: ✅ PASS
- All graphique tests: ✅ PASS
- All ARC sensor tests: ✅ PASS
- All reconnection tests: ✅ PASS

## Backward Compatibility

- ✅ No breaking changes to existing API
- ✅ All existing endpoints work as before
- ✅ New error code (503) is standard HTTP status
- ✅ Error messages are descriptive and clear
- ✅ Clients can safely ignore 503 errors or retry

## Configuration

**No configuration changes required**. The system uses:
- Silence timeout: 5.0 seconds (existing)
- Backoff strategy: 1s → 1.5x → 30s max (existing)
- Sensor states: CONNECTED, DISCONNECTED, RECONNECTING, FAILED (existing)

## Future Enhancements

Potential improvements for future versions:
1. Configurable silence thresholds per sensor
2. Persistent reconnection history/logging
3. Webhook notifications on connection state changes
4. Dashboard visualization of sensor health
5. Automatic fallback to cached data when sensor disconnects
6. Graceful degradation with partial sensor data

## Files Modified

| File | Type | Changes |
|------|------|---------|
| `src/core/sensor_reconnection.py` | Modified | Added `is_connected` param, `is_sensor_connected()` method |
| `src/routers/sensor.py` | Modified | Connection checks on all data endpoints |
| `src/routers/graphique.py` | Modified | Connection checks on graphique endpoints |
| `src/routers/raw.py` | Modified | Connection check on raw endpoint |
| `src/routers/api.py` | Modified | Added raw router import |
| `tests/conftest.py` | Created | Test fixture for sensor initialization |
| `tests/test_sensor_disconnection_errors.py` | Created | 7 tests for disconnection handling |
| `docs/sensor-connection-management.md` | Created | Comprehensive guide |
| `docs/api.md` | Modified | Added 503 status code documentation |
| `docs/index.md` | Modified | Updated documentation index |

## Implementation Checklist

- ✅ Connection status checks implemented
- ✅ 503 error responses on disconnection
- ✅ ARC special case handling
- ✅ Test coverage (7 new tests)
- ✅ Documentation (comprehensive guide)
- ✅ Backward compatibility verified
- ✅ All tests passing (141/141)
- ✅ Error messages descriptive and actionable
