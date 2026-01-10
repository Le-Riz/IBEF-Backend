# API overview

The IBEF Backend exposes a comprehensive REST API for data acquisition, sensor management, test execution, and history tracking.

## Endpoints

### Meta

- `GET /` – Service info: `{ "message": "IBEF Backend API" }`
- `GET /health` – Health check: `{ "status": "ok", "app": "IBEF Backend API" }`

### Data

- `GET /api/data/point/{sensor_id}` – Latest point: `{ "time": float, "value": float }`
- `GET /api/data/list/{sensor_id}` – Point history: `{ "list": [{ "time": float, "value": float }, ...] }`

### Raw

- `GET /api/raw/point/{sensor_id}` – Raw data point: `{ "time": float, "value": float }`

### Test

- `PUT /api/test/start` – Start test session: `{}` (accepts optional field list)
- `PUT /api/test/stop` – Stop test session: `{}`

### History

- `GET /api/history/list` – List available histories: `{ "list": ["name1", "name2", ...] }`
- `GET /api/history/{name}?download=false` – Get history metadata: `{ "fields": [...] }`
- `GET /api/history/{name}?download=true` – Download history as zip file
- `PUT /api/history/{name}` – Update history: `{}`
- `POST /api/history/{name}` – Modify fields: `{}` (accepts field list)
- `DELETE /api/history/{name}` – Delete history: `{}`

## Quick test

```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/api/data/point/force | jq
```

## Interactive docs

Explore and test all endpoints interactively:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Both auto-generate from OpenAPI spec with accurate request/response schemas.
