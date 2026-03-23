# Developer Guide

## Architecture Overview

```
src/
├── main.py                 # FastAPI application entry point
├── schemas.py             # Pydantic response models
├── core/                  # Core business logic
│   ├── config_loader.py   # Configuration management
│   ├── service_manager.py # Service orchestration
│   ├── models/            # Data structures and models
│   ├── services/          # Microservices (sensor, serial, test)
│   └── processing/        # Data processing pipeline
└── routers/               # API endpoints
    ├── api.py            # Main router aggregation
    ├── sensor.py         # Sensor operations
    ├── test.py           # Test management
    ├── history.py        # Historical data
    └── graphique.py      # Data visualization
```

## Core Services

### Sensor Manager
::: src.core.services.sensor_manager
    options:
      show_root_heading: false

### Serial Handler
::: src.core.services.serial_handler
    options:
      show_root_heading: false

### Test Manager
::: src.core.services.test_manager
    options:
      show_root_heading: false

## Configuration

### Config Loader
::: src.core.config_loader
    options:
      show_root_heading: false

## Development Workflow

### Setup
```bash
# Create virtual environment
bash scripts/create_venv.sh

# Install with dev dependencies
pip install -e '.[dev]'
```

### Running the Application
```bash
# Start the server
python src/main.py
```

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src
```

## Type Safety

The project uses **type hints throughout** for better IDE support and error catching. Always include type annotations in new code:

```python
def process_sensor_data(
    sensor_id: SensorId,
    value: float,
    timestamp: float
) -> Point:
    """Process raw sensor data."""
    return Point(time=timestamp, value=value)
```

## Documentation Standards

### Docstring Style

Use Google-style docstrings for consistency:

```python
def calculate_moving_average(
    values: list[float],
    window_size: int = 10
) -> float:
    \"\"\"Calculate moving average of values.
    
    Args:
        values: List of numeric values.
        window_size: Number of recent values to average.
        
    Returns:
        Moving average as float.
        
    Raises:
        ValueError: If window_size exceeds list length.
    \"\"\"
    if window_size > len(values):
        raise ValueError("Window size exceeds list length")
    return sum(values[-window_size:]) / window_size
```

### Module Docstrings

Every module should have a top-level docstring:

```python
\"\"\"Module description.

Brief explanation of what this module does.
\"\"\"
```
