#!/usr/bin/env python3
"""
Export OpenAPI schema from FastAPI app to JSON file.
This allows the API documentation to be included in static MkDocs site.
"""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import app

if __name__ == "__main__":
    output_file = Path(__file__).parent.parent / "docs" / "assets" / "openapi.json"
    
    # Generate OpenAPI schema
    openapi_schema = app.openapi()
    
    # Write to file
    with open(output_file, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    
    print(f"✓ OpenAPI schema exported to {output_file}")
    print(f"  Title: {openapi_schema.get('info', {}).get('title')}")
    print(f"  Version: {openapi_schema.get('info', {}).get('version')}")
    print(f"  Endpoints: {len(openapi_schema.get('paths', {}))}")
