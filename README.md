# IBEF Backend API

FastAPI backend for the IBEF project, managed with Hatch.

## Quick start

```bash
# install hatch if missing
pipx install hatch

# install dependencies and run the dev server
hatch run api
```

Alternatively, on Unix systems:

```bash
./run.sh          # runs the API dev server (default)
./run.sh api      # runs the API dev server
./run.sh test     # runs the test suite
./run.sh doc      # starts the documentation server
```

## Development

```bash
# start dev server
hatch run api
# or: ./run.sh
# or: ./run.sh api

# run tests
hatch run test
# or: ./run.sh test

# lint with ruff
hatch run lint

# type-check
hatch run typecheck

# serve documentation
hatch run docs:serve
# or: ./run.sh doc
```

## Documentation

MkDocs is configured with Material and mkdocstrings.

```bash
# live docs server
hatch run docs:serve

# export OpenAPI schema
hatch run export-openapi
# or: ./run.sh export-openapi

# build static docs (with OpenAPI schema)
hatch run docs:export-schema
# or: ./run.sh build-docs
```

The documentation includes:
- **Interactive API Reference** — Full OpenAPI/Swagger documentation embedded in MkDocs
- **API Overview** — Quick reference with examples
- **Developer Guide** — Architecture and performance details

## Project layout

- src/: application code with `main.py`, routers, and schemas
- docs/: MkDocs sources
- tests/: test suite
- pyproject.toml: project metadata, dependencies, and Hatch envs

## API structure

- `GET /health`
  - Returns: `{"status": "ok", "app": "IBEF Backend API"}`
  
- `GET /api`
  - `/sensor/{sensor_id}` — Sensor data operations (FORCE, DISP_1, DISP_2, DISP_3, ARC)
    - **ARC** is a calculated sensor representing circular deflection: `ARC = DISP_1 - (DISP_2 + DISP_3) / 2`
    - `GET /data` → Latest calibrated data point: `{"time": float, "value": float}`
    - `GET /data/history?window={30,60,120,300,600}` → Fixed-count history with uniform spacing
      - Returns exactly 300 points regardless of window duration
      - Uses 10 Hz processing rate for point spacing
    - `GET /raw` → Latest raw/uncalibrated data point (physical sensors only)
    - `PUT /zero` → Calibrate sensor (zero reference)
  - `/test` — Test session management
    - `PUT /start` → Start test with metadata payload
    - `PUT /stop` → Stop current test session
  - `/history` — Test history persistence and retrieval
    - `GET /` → List all test IDs
    - `GET /{name}` → Get test metadata
    - `GET /{name}/download` → Download test data as ZIP
    - `PUT /{name}` → Update test metadata
    - `PUT /{name}/archive` → Move test to archive
    - `DELETE /{name}` → Permanently delete test

## Performance optimizations

### Circular Buffer (O(1) operations)
- **`__slots__`**: Fixed attribute list reduces memory overhead
- **Power-of-2 capacity**: Uses bitwise AND instead of modulo for 3-5x faster indexing
- **Precomputed windows**: All window offsets calculated at initialization (O(1) retrieval)
- **10 Hz processing rate**: Point spacing reflects actual data delivery rate, not raw sensor frequency

### Data Storage
- **Fixed point count**: 300 points per duration window (30s, 60s, 120s, 300s, 600s) ensures consistent memory usage
- **O(1) bulk retrieval**: Optimized `get_all()` detects buffer wrap state for fastest access
- **No dynamic computation**: All window info precomputed; query time is deterministic

### Test History
- **Persistent storage**: Metadata in JSON, raw data in CSV with circular buffer backup
- **Archive support**: Move old tests to archived_data folder without deleting
- **Concurrent test support**: Each test has independent sensor buffers