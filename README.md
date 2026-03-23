# IBEF Backend API

FastAPI backend for the IBEF project.

## Requirements

- Python 3.10+
- Linux/macOS shell for helper scripts (`run.sh`, `scripts/*.sh`)

## Quick Start

### Option 1: Virtual environment + pip (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]

# Start API
cd src && uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Helper script

```bash
./run.sh          # same as: ./run.sh api
./run.sh api      # run API dev server
./run.sh doc      # generate OpenAPI + serve MkDocs
./run.sh build-docs
./run.sh export-openapi
```

## Development Commands

```bash
# API
cd src && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Lint
ruff check src

# Type check
mypy src

# Documentation
python scripts/export_openapi.py
mkdocs serve
mkdocs build
```

## Documentation

This project uses MkDocs + Material.

```bash
# Local docs with live reload
python scripts/export_openapi.py
mkdocs serve

# Generate OpenAPI schema consumed by docs
python scripts/export_openapi.py

# Build static docs (OpenAPI export + mkdocs build)
python scripts/export_openapi.py && mkdocs build
```

The CI workflow in `.github/workflows/docs.yml` builds and deploys docs on pushes to `main`.

## Project Layout

- `src/`: application code (FastAPI app, routers, core services, schemas)
- `docs/`: MkDocs content
- `config/`: runtime configuration files (including sensor config)
- `scripts/`: helper scripts (venv setup, systemd setup, OpenAPI export)
- `storage/`: test data and archives
- `pyproject.toml`: dependencies and project metadata

## Systemd Service (Linux)

If you want the backend to run as a service:

```bash
./scripts/setup_systemd.sh
```

This script installs `ibef-backend.service`, replaces `<CHANGE_ME>` with the current project path, reloads systemd, enables, and restarts the service.