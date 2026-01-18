# ARC Sensor (Circular Deflection)

## Overview

The ARC sensor is a **calculated sensor** that represents the circular deflection (fléche circulaire) of a test specimen. Unlike physical sensors (FORCE, DISP_1, DISP_2, DISP_3, DISP_4, DISP_5), ARC is computed in real-time from the primary three displacement sensors.

## Calculation Formula

```python
ARC = DISP_1 - (DISP_2 + DISP_3) / 2
```

## Physical Interpretation

The ARC value represents the deviation of the central displacement sensor (DISP_1) from the average of the two outer displacement sensors (DISP_2 and DISP_3). This measurement is useful for:

- **Circular deflection analysis**: Detecting non-uniform deformation
- **Material testing**: Understanding bending behavior in specimens
- **Quality control**: Identifying asymmetric loading conditions

## Usage

### API Endpoints

ARC is accessible through the same API endpoints as physical sensors:

```bash
# Get latest ARC value
GET /api/sensor/ARC/data

# Get ARC history
GET /api/sensor/ARC/data/history?window=60

# Zero calibration (applies to component sensors)
PUT /api/sensor/ARC/zero
```

### Example Response

```json
{
  "time": 123.456,
  "value": 2.5
}
```

### Data Storage

ARC values are automatically included in test data files:

- **data.csv**: Contains ARC column alongside FORCE, DISP_1, DISP_2, DISP_3, DISP_4, DISP_5
- **Circular buffers**: ARC has its own buffer for real-time history access
- **Test archives**: ARC data is preserved in archived tests

## Implementation Details

### Calculation Location

ARC is calculated in the `DataProcessor` class at 20 Hz (configurable via `PROCESSING_RATE`):

```python
# src/core/processing/data_processor.py
arc_value = values[DISP_1] - (values[DISP_2] + values[DISP_3]) / 2
values[SensorId.ARC.value] = arc_value
```

### Sensor ID

```python
from core.models.sensor_enum import SensorId

SensorId.ARC  # Value: 4
```

### Storage

- **Enum position**: `SensorId.ARC = 4`
- **Buffer size**: Same as other sensors (10 minutes at 20 Hz)
- **CSV column**: Alphabetically sorted in output files

## Example Use Cases

### 1. Detecting Asymmetric Loading

```python
# If ARC ≈ 0: symmetric loading (DISP_1 = avg(DISP_2, DISP_3))
# If ARC > 0: center deflects more than average of sides
# If ARC < 0: center deflects less than average of sides
```

### 2. Three-Point Bending Test Analysis

In a three-point bending test:
- DISP_1: Central load point displacement
- DISP_2, DISP_3: Support point displacements (DISP_4/DISP_5 are additional channels not used in ARC)
- ARC: True specimen deflection (accounting for support settlement)

### 3. Quality Control Threshold

```python
# Alert if circular deflection exceeds threshold
if abs(arc_value) > 10.0:
    log_warning("Excessive circular deflection detected")
```

## Testing

Comprehensive test coverage is provided in `tests/test_arc_sensor.py`:

- ✅ Enum definition verification
- ✅ Formula calculation validation
- ✅ API endpoint accessibility
- ✅ Data persistence in test files
- ✅ Case-insensitive sensor ID handling

Run tests with:

```bash
hatch run pytest tests/test_arc_sensor.py -v
```

## Technical Notes

- **No raw data**: ARC is calculated, not measured, so `/data/raw` endpoint behavior may differ
- **Zero calibration**: Zeroing ARC affects the underlying displacement sensors
- **Real-time calculation**: Computed on every data frame (20 Hz default)
- **Minimal overhead**: O(1) calculation added to processing loop
