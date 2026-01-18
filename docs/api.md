# API overview

The IBEF Backend exposes a comprehensive REST API for data acquisition, sensor management, test execution, and history tracking.

!!! tip "Interactive Documentation"
    For a complete, interactive API reference with all endpoints, schemas, and the ability to try requests, see the **[API Reference](api-reference.md)** page (powered by ReDoc/OpenAPI).

All endpoints follow RESTful principles with clear resource identification and consistent response codes:

- **200 OK**: Successful GET request with response body
- **204 No Content**: Successful PUT/POST/DELETE request without response body
- **400 Bad Request**: Invalid request parameters
- **404 Not Found**: Resource not found
- **503 Service Unavailable**: Requested sensor is not currently connected (see [Sensor Connection Management](sensor-connection-management.md))

## Meta Endpoints

### Service Information

**`GET /`**

Returns basic service information.

**Response:**

```json
{
  "message": "IBEF Backend API"
}
```

### Health Check

**`GET /health`**

Check if the API is running and healthy.

**Response:**

```json
{
  "status": "ok",
  "app": "IBEF Backend API"
}
```

---

## Sensor Endpoints

All sensor operations are grouped under `/api/sensor/{sensor_id}` where `sensor_id` can be:

- `FORCE` - Force sensor
- `DISP_1`, `DISP_2`, `DISP_3`, `DISP_4`, `DISP_5` - Displacement sensors

### Get Latest Calibrated Data

**`GET /api/sensor/{sensor_id}/data`**

Get the most recent calibrated data point from a specific sensor.

**Response:**

```json
{
  "time": 1234567890.123,
  "value": 42.5
}
```

**Example:**

```bash
curl http://localhost:8000/api/sensor/FORCE/data
```

### Get Data History

**`GET /api/sensor/{sensor_id}/data/history`**

Get historical calibrated data points from a specific sensor with uniform point spacing.

**Query Parameters:**

- `window` (optional, int) - Time window in seconds: 30, 60, 120, 300, or 600 (default: 30)

**Response:**

Always returns exactly **300 points** regardless of window duration, with uniform spacing based on 10 Hz processing rate.

```json
{
  "list": [
    { "time": 1234567890.123, "value": 42.5 },
    { "time": 1234567890.223, "value": 42.6 },
    { "time": 1234567890.323, "value": 42.7 }
  ]
}
```

**Point spacing by window:**

- 30s window: 0.1s spacing (30s ÷ 300 points)
- 60s window: 0.2s spacing
- 120s window: 0.4s spacing
- 300s window: 1.0s spacing
- 600s window: 2.0s spacing

**Examples:**

```bash
# Get 30-second history (0.1s point spacing)
curl http://localhost:8000/api/sensor/FORCE/data/history?window=30

# Get 5-minute history (1.0s point spacing)
curl http://localhost:8000/api/sensor/FORCE/data/history?window=300
```

**Note:** If fewer than the requested window of data is available, the endpoint returns all available points up to 300, maintaining uniform spacing.

### Get Latest Raw Data

**`GET /api/sensor/{sensor_id}/raw`**

Get the most recent raw (uncalibrated) data point from a specific sensor.

**Response:**

```json
{
  "time": 1234567890.123,
  "value": 42.5
}
```

**Example:**

```bash
curl http://localhost:8000/api/sensor/FORCE/raw
```

### Zero/Calibrate Sensor

**`PUT /api/sensor/{sensor_id}/zero`**

Zero (calibrate) a sensor by recording its current value as the zero reference. All future readings from this sensor will be adjusted by subtracting this reference value.

**Response:**

```text
204 No Content
```

**Example:**

```bash
curl -X PUT http://localhost:8000/api/sensor/FORCE/zero
```

---

## Test Management Endpoints

### Start Test

**`PUT /api/test/start`**

Start a new test session with optional metadata.

**Request Body (optional):**

```json
{
  "test_id": "test_001",
  "date": "2026-01-10",
  "operator_name": "John Doe",
  "specimen_code": "SPEC001",
  "dim_length": 100.0,
  "dim_height": 50.0,
  "dim_width": 25.0,
  "loading_mode": "compression",
  "sensor_spacing": 10.0,
  "ext_support_spacing": 20.0,
  "load_point_spacing": 15.0
}
```

**Response:**

```text
204 No Content
```

### Stop Test

**`PUT /api/test/stop`**

Stop the current test session.

**Response:**

```text
204 No Content
```

**Example:**

```bash
curl -X PUT http://localhost:8000/api/test/stop
```

---

## History Management Endpoints

### List All Tests

**`GET /api/history`**

List all available test histories.

**Response:**

```json
{
  "list": ["test_001", "test_002", "test_003"]
}
```

### Get Test Metadata

**`GET /api/history/{name}`**

Get metadata for a specific test.

**Response:**

```json
{
  "test_id": "test_001",
  "date": "2026-01-10",
  "operator_name": "John Doe",
  "specimen_code": "SPEC001",
  "dim_length": 100.0,
  "dim_height": 50.0,
  "dim_width": 25.0,
  "loading_mode": "compression",
  "sensor_spacing": 10.0,
  "ext_support_spacing": 20.0,
  "load_point_spacing": 15.0
}
```

**Example:**

```bash
curl http://localhost:8000/api/history/test_001
```

### Download Test Data

**`GET /api/history/{name}/download`**

Download complete test data as a ZIP file.

**Response:**

```text
application/zip
(binary file content)
```

**Example:**

```bash
curl -O http://localhost:8000/api/history/test_001/download
```

### Update Test Metadata

**`PUT /api/history/{name}`**

Update metadata for a specific test.

**Request Body:**

```json
{
  "test_id": "test_001",
  "date": "2026-01-10",
  "operator_name": "Jane Smith",
  "specimen_code": "SPEC002",
  "dim_length": 150.0,
  "dim_height": 60.0,
  "dim_width": 30.0,
  "loading_mode": "tension",
  "sensor_spacing": 12.0,
  "ext_support_spacing": 25.0,
  "load_point_spacing": 18.0
}
```

**Response:**

```text
204 No Content
```

**Example:**

```bash
curl -X PUT http://localhost:8000/api/history/test_001 \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Archive Test

**`PUT /api/history/{name}/archive`**

Archive a test by moving it to archived storage.

**Response:**

```text
204 No Content
```

**Example:**

```bash
curl -X PUT http://localhost:8000/api/history/test_001/archive
```

### Delete Test

**`DELETE /api/history/{name}`**

Permanently delete a test and all its data.

**Response:**

```text
204 No Content
```

**Example:**

```bash
curl -X DELETE http://localhost:8000/api/history/test_001
```

---

## Quick Test Examples

```bash
# Health check
curl -s http://localhost:8000/health | jq

# Get latest force sensor data
curl -s http://localhost:8000/api/sensor/FORCE/data | jq

# Get 30-second history (0.1s point spacing, 300 points)
curl -s http://localhost:8000/api/sensor/DISP_1/data/history?window=30 | jq

# Get 5-minute history (1.0s point spacing, 300 points)
curl -s http://localhost:8000/api/sensor/DISP_1/data/history?window=300 | jq

# Zero a sensor
curl -X PUT http://localhost:8000/api/sensor/FORCE/zero

# List all test histories
curl -s http://localhost:8000/api/history | jq

# Get test metadata
curl -s http://localhost:8000/api/history/test_001 | jq

# Start a test
curl -X PUT http://localhost:8000/api/test/start \
  -H "Content-Type: application/json" \
  -d '{
    "test_id": "test_001",
    "date": "2026-01-10",
    "operator_name": "John Doe",
    "specimen_code": "SPEC001",
    "dim_length": 100.0,
    "dim_height": 50.0,
    "dim_width": 25.0,
    "loading_mode": "compression",
    "sensor_spacing": 10.0,
    "ext_support_spacing": 20.0,
    "load_point_spacing": 15.0
  }'

# Download test data
curl -O http://localhost:8000/api/history/test_001/download
```

---

## Interactive Documentation

Explore and test all endpoints interactively:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Both interfaces auto-generate from the OpenAPI specification with accurate request/response schemas.
