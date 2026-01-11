# Developer guide

## Prerequisites

- Python 3.10+
- [Hatch](https://hatch.pypa.io) (install with `pipx install hatch`)

## Common tasks

```bash
# start dev server
hatch run api
# or: ./run.sh
# or: ./run.sh api

# run tests
hatch run test
# or: ./run.sh test

# lint
hatch run lint

# type-check
hatch run typecheck

# serve documentation
hatch run docs:serve
# or: ./run.sh doc

# build static docs
hatch run docs:build
```

## Documentation

```bash
# live docs server
hatch run docs:serve
# or: ./run.sh doc

# build static site
hatch run docs:build
```

MkDocs sources live under `docs/`. Adjust navigation in `mkdocs.yml` when adding new pages.

---

## Architecture

### Core Components

**CircularBuffer** (`src/core/models/circular_buffer.py`)
- Fixed-capacity buffer with O(1) append and access
- Optimized for speed: `__slots__`, bitwise modulo for power-of-2 capacities
- Supports bulk retrieval with automatic wrap detection

**SensorDataStorage** (`src/core/models/circular_buffer.py`)
- Manages multiple sensor buffers (FORCE, DISP_1, DISP_2, DISP_3)
- Precomputes all window offsets at initialization (O(1) lookup)
- Returns exactly 300 points per duration with uniform spacing

**DataProcessor** (`src/core/processing/data_processor.py`)
- Runs at **10 Hz** (100ms intervals)
- Receives raw sensor data, applies calibration, stores in circular buffers
- Publishes `data_received` event for each point

**TestManager** (`src/core/services/test_manager.py`)
- Manages test lifecycle: start, stop, pause, resume
- Persists data to disk (metadata.json, data.csv, raw.log)
- Integrates with circular buffers via SensorDataStorage
- Publishes test state change events

### Data Flow

```
Serial Data → SerialHandler → DataProcessor (10 Hz) → Circular Buffers
                                        ↓
                        Published: data_received event
                                        ↓
                        API endpoints consume buffer data
                                        ↓
                        TestManager persists on disk
```

### Storage

- **`storage/data/`** — Active test data (temporary, cleared between tests)
- **`storage/data/test_data/`** — Persistent test histories
- **`storage/data/archived_data/`** — Archived tests

Each test directory contains:
- `metadata.json` — Test metadata (TestMetaData model)
- `data.csv` — Processed sensor data
- `raw.log` — Raw uncalibrated data

---

## Performance Characteristics

### Insertion (append)
- **Time:** O(1) constant time
- **Speed:** Single tuple assignment + index update
- **Memory:** Fixed capacity, no reallocation

### History Query (`get_data_for_window_seconds`)
- **Time:** O(1) for full windows (uses precomputed offsets)
- **Time:** O(n) for partial windows (n = number of points)
- **Maximum points:** 300 (fixed, ensures predictable latency)

### Bulk Retrieval (`get_all`)
- **Time:** O(n) where n = number of valid points
- **Speed:** Direct memory access, automatic wrap-aware copy

### Test History List
- **Time:** O(1) — reads test_manager.test_history list
- **Storage:** Disk I/O only on test start/stop

---

## Testing

Run the full test suite:
```bash
hatch run test
```

Test coverage includes:
- **CircularBuffer** — Insertion, retrieval, wrapping, bulk access
- **SensorDataStorage** — Multi-sensor storage, window queries
- **DataProcessor** — 10 Hz rate, calibration, event publishing
- **Sensor API** — Get data, history with window parameter, zero calibration
- **Test Management** — Start/stop, metadata persistence
- **History API** — List, get, download, update, archive, delete

**Current status:** 65 tests passing (100%)

---

## Adding New Features

### New Sensor Endpoint
1. Add route to `src/routers/sensor.py`
2. Query `test_manager.get_sensor_data()` or `get_sensor_history()`
3. Return `Point` or `PointsList` model

### New History Operation
1. Add method to `TestManager` class
2. Add route to `src/routers/history.py`
3. Call TestManager method and return appropriate status

### Changing Processing Rate
1. Update `PROCESSING_RATE` constant in `src/core/processing/data_processor.py`
2. Update TestManager's `effective_freq` calculation
3. Rebuild SensorDataStorage to recalculate point spacing
4. Update API documentation with new spacing values
