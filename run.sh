#!/bin/bash
set -euo pipefail

ensure_docs_dependencies() {
  if ! python -m pip show mkdocs-material >/dev/null 2>&1; then
    echo "Missing documentation dependency: mkdocs-material"
    echo "Install docs dependencies with one of:"
    echo "  python -m pip install '.[dev]'"
    echo "  python -m pip install mkdocs mkdocs-material 'mkdocstrings[python]'"
    exit 1
  fi
}

case "${1:-api}" in
  api)
    cd src && uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ;;
  doc)
    ensure_docs_dependencies
    python scripts/export_openapi.py
    python -m mkdocs serve
    ;;
  export-openapi)
    ensure_docs_dependencies
    python scripts/export_openapi.py && python -m mkdocs build
    ;;
  build-docs)
    ensure_docs_dependencies
    python scripts/export_openapi.py && python -m mkdocs build
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
