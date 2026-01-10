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
./run.sh        # runs the API dev server
./run.sh test   # runs the test suite
```

## Development

```bash
# start dev server
hatch run api
# or: ./run.sh

# run tests
hatch run test
# or: ./run.sh test

# lint with ruff
hatch run lint

# type-check
hatch run typecheck
```

## Documentation

MkDocs is configured with Material and mkdocstrings.

```bash
# live docs server
hatch run docs:serve

# build static docs
hatch run docs:build
```

## Project layout

- src/: application code with `main.py`, routers, and schemas
- docs/: MkDocs sources
- tests/: test suite
- pyproject.toml: project metadata, dependencies, and Hatch envs

## API structure

- `GET /health`
  - Returns: `{"status": "ok", "app": "IBEF Backend API"}`
  
- `GET /api`
  - `/data`
    - `GET /point/{sensor_id}` → `{"time": float, "value": float}`
    - `GET /list/{sensor_id}` → `{"list": [{"time": float, "value": float}, ...]}`
  - `/raw`
    - `GET /point/{sensor_id}` → `{"time": float, "value": float}`
  - `/test`
    - `PUT /start` (with optional field list) → `{}`
    - `PUT /stop` → `{}`
  - `/history`
    - `GET /list` → `{"list": ["name1", "name2", ...]}`
    - `DELETE /{name}` → `{}`
    - `PUT /{name}` → `{}`
    - `POST /{name}` (with field list) → `{}`
    - `GET /{name}?download=false` → `{"fields": [...]}`
    - `GET /{name}?download=true` → `{zip file}`