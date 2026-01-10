# API overview

The service currently exposes a minimal set of endpoints for health and metadata.

## Endpoints

- `GET /` returns a short message with the app name.
- `GET /health` returns `{ "status": "ok" }` and can be used for probes.

## Quick test

```bash
curl -s http://localhost:8000/health | jq
```

You can explore and try requests in the automatic docs once the server is running:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Next steps

Add new routers under `src/ibef_backend` and include them in `app` using `include_router`.
