#!/bin/bash
set -euo pipefail

case "${1:-api}" in
  api)
    hatch run api
    ;;
  test)
    hatch run test
    ;;
  doc)
    hatch run docs:serve
    ;;
  export-openapi)
    hatch run export-openapi
    ;;
  build-docs)
    hatch run docs:export-schema
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
