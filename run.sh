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
  *)
    echo "Usage: $0 [api|test|doc]"
    echo "  api  (default) - Start the API development server"
    echo "  test           - Run the test suite"
    echo "  doc            - Start the documentation server"
    exit 1
    ;;
esac
