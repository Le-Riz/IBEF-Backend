#!/bin/bash
set -euo pipefail

if [ "${1:-}" = "test" ]; then
  hatch run test
else
  hatch run api
fi
