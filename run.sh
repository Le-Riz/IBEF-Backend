#!/bin/bash
set -euo pipefail

case "${1:-api}" in
  api)
    cd src && uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ;;
  test)
    pytest
    ;;
  doc)
    python scripts/export_openapi.py
    mkdocs serve
    ;;
  export-openapi)
    python scripts/export_openapi.py && mkdocs build
    ;;
  build-docs)
    python scripts/export_openapi.py && mkdocs build
    ;;
  *)
    echo "Usage: $0 [api|test|doc|export-openapi|build-docs]"
    echo "  api            (default) - Start the API development server"
    echo "  test                     - Run the test suite"
    echo "  doc                      - Start the documentation server"
    echo "  export-openapi           - Export OpenAPI schema to docs/"
    echo "  build-docs               - Export schema and build static docs"
    exit 1
    ;;
esac
