# IBEF Backend API

IBEF Backend is a FastAPI service for real-time sensor data acquisition, processing, and persistent test management.

## Features

- **Real-time data acquisition** — 20 Hz processing rate with 6 sensors (FORCE, DISP_1, DISP_2, DISP_3, DISP_4, DISP_5)
- **Optimized storage** — Circular buffers with O(1) insertion and retrieval
- **Fixed-point history** — Exactly 300 points per window (30s, 60s, 2m, 5m, 10m) with uniform spacing
- **Test management** — Start, stop, archive, and delete test sessions
- **Persistent storage** — Metadata in JSON, data in CSV with backup log files
- **REST API** — Full CRUD operations on sensors and test histories

## Quick start

```bash
# Start the API server
./run.sh
# or: hatch run api

# Run tests
./run.sh test

# View documentation
./run.sh doc
```

Then open http://localhost:8000/docs for the interactive API documentation (or http://localhost:8000 for MkDocs when using `./run.sh doc`).

## Key Components

- **Circular Buffers** — O(1) insertion with 0.1s to 2.0s point spacing depending on window
- **Data Processor** — 10 Hz rate, applies calibration, publishes events
- **Test Manager** — Handles test lifecycle and disk persistence
- **REST API** — Sensor data, history queries, and test management endpoints

## API Endpoints

- `GET /api/sensor/{sensor_id}/data` — Latest calibrated data
- `GET /api/sensor/{sensor_id}/data/history?window=30` — 300 points with uniform spacing
- `PUT /api/test/start` — Start a new test session
- `PUT /api/test/stop` — Stop current test
- `GET /api/history` — List all test histories
- `GET /api/history/{name}/download` — Download test data as ZIP
- `PUT /api/history/{name}/archive` — Archive a test

## Documentation

- **[API Reference (Interactive)](api-reference.md)** — Full OpenAPI documentation with ReDoc
- **[API Overview](api.md)** — Quick reference and examples
- **[Sensor Connection Management](sensor-connection-management.md)** — Connection states, reconnection strategy, error handling
- **[Sensor Configuration](sensor-config.md)** — Sensor setup and calibration
- **[Auto-Detection](auto-sensor-detection.md)** — Automatic port detection
- **[ARC Sensor](arc-sensor.md)** — ARC calculation and usage
- **[Developer Guide](dev.md)** — Architecture, performance, and contribution guidelines
