from fastapi import APIRouter, HTTPException
import time
import math
from core.models.sensor_enum import SensorId
from core.models.circular_buffer import DisplayDuration
from core.event_hub import event_hub
from core.services.sensor_manager import sensor_manager
from core.services.test_manager import test_manager

from schemas import Point, PointsList, OffsetResponse

VALID_SENSOR_VALUES = ", ".join([s.name for s in SensorId])

router = APIRouter(prefix="/sensor", tags=["sensor"])


def _interpolate_small_nan_gaps(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Replace NaN runs of length ≤2 by linear interpolation; drop longer runs.
    Keeps chronological order and removes any remaining NaN to avoid JSON errors.
    """
    cleaned: list[tuple[float, float]] = []
    i = 0
    n = len(points)
    while i < n:
        t, v = points[i]
        if not math.isnan(v):
            cleaned.append((t, v))
            i += 1
            continue

        # Start of a NaN run
        start = i
        while i < n and math.isnan(points[i][1]):
            i += 1
        end = i - 1
        run_len = end - start + 1

        prev_point = cleaned[-1] if cleaned else None
        next_point = points[i] if i < n else None

        can_interpolate = (
            run_len <= 2 and prev_point is not None and next_point is not None
            and not math.isnan(prev_point[1]) and not math.isnan(next_point[1])
        )

        if can_interpolate:
            # Linear interpolation across the gap (distributes points evenly)
            gap_time = next_point[0] - prev_point[0]
            gap_value = next_point[1] - prev_point[1]
            steps = run_len + 1
            for k in range(1, run_len + 1):
                factor = k / steps
                interp_t = prev_point[0] + gap_time * factor
                interp_v = prev_point[1] + gap_value * factor
                cleaned.append((interp_t, interp_v))
        # Otherwise: drop this NaN run (leave a gap)

    return cleaned


@router.get("/{sensor_id}/data", response_model=Point, responses={
    400: {
        "description": "Invalid sensor_id provided.",
        "content": {
            "application/json": {
                "example": {"detail": f"Invalid sensor_id: INVALID. Valid values are: {VALID_SENSOR_VALUES}"}
            }
        }
    },
    503: {
        "description": "Sensor is not currently connected.",
        "content": {
            "application/json": {
                "example": {"detail": "Sensor FORCE is not connected"}
            }
        }
    }
})
async def get_sensor_data(sensor_id: str) -> Point:
    """
    Get the latest data point from a sensor (calibrated/processed value).
    Time is relative to test start if a test is running, otherwise 0.
    """
    # Validate sensor_id
    try:
        sid = SensorId[sensor_id.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sensor_id: {sensor_id}. Valid values are: {VALID_SENSOR_VALUES}"
        )

    # Check sensor connection status
    if not sensor_manager.is_sensor_connected(sid):
        raise HTTPException(
            status_code=503,
            detail=f"Sensor {sensor_id.upper()} is not connected"
        )

    idx = sid.value
    corrected = sensor_manager.sensors[idx]
    relative_time = test_manager.get_relative_time()
    return Point(time=relative_time, value=corrected)


@router.get("/{sensor_id}/data/history", response_model=PointsList, responses={
    400: {
        "description": "Invalid sensor_id or window parameter.",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_sensor": {"value": {"detail": f"Invalid sensor_id: INVALID. Valid values are: {VALID_SENSOR_VALUES}"}},
                    "invalid_window": {"value": {"detail": "Invalid window: 45. Allowed values are: [30, 60, 120, 300, 600]"}}
                }
            }
        }
    },
    409: {
        "description": "No test is currently running.",
        "content": {
            "application/json": {
                "example": {"detail": "No test is currently running"}
            }
        }
    },
    503: {
        "description": "Sensor is not currently connected.",
        "content": {
            "application/json": {
                "example": {"detail": "Sensor FORCE is not connected"}
            }
        }
    }
})
async def get_sensor_data_history(sensor_id: str, window: int = 30) -> PointsList:
    """
    Get historical data points from a sensor (calibrated/processed values).
    Window is expressed in seconds and must be one of: 30, 60, 120, 300, 600.
    Returns a fixed number of points (based on 30s sampling) evenly spaced across the window.
    """
    # Validate sensor_id
    try:
        sid = SensorId[sensor_id.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sensor_id: {sensor_id}. Valid values are: {VALID_SENSOR_VALUES}"
        )

    # Check sensor connection status
    if not sensor_manager.is_sensor_connected(SensorId[sensor_id.upper()]):
        raise HTTPException(
            status_code=503,
            detail=f"Sensor {sensor_id.upper()} is not connected"
        )

    allowed_windows = {d.value_seconds() for d in DisplayDuration}
    if window not in allowed_windows:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window: {window}. Allowed values are: {sorted(allowed_windows)}"
        )

    try:
        data_points = test_manager.get_sensor_history(sid, window)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    cleaned_points = _interpolate_small_nan_gaps(data_points)
    points = [Point(time=t, value=v) for t, v in cleaned_points]
    return PointsList(list=points)


@router.get("/{sensor_id}/raw", response_model=Point, responses={
    400: {
        "description": "Invalid sensor_id provided.",
        "content": {
            "application/json": {
                "example": {"detail": f"Invalid sensor_id: INVALID. Valid values are: {VALID_SENSOR_VALUES}"}
            }
        }
    },
    503: {
        "description": "Sensor is not currently connected.",
        "content": {
            "application/json": {
                "example": {"detail": "Sensor FORCE is not connected"}
            }
        }
    }
})
async def get_sensor_raw_data(sensor_id: str) -> Point:
    """
    Get the latest raw (uncalibrated) data point from a sensor.
    Time is relative to test start if a test is running, otherwise 0.
    """
    # Validate sensor_id
    try:
        sid = SensorId[sensor_id.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sensor_id: {sensor_id}. Valid values are: {VALID_SENSOR_VALUES}"
        )

    # Check sensor connection status
    if not sensor_manager.is_sensor_connected(sid):
        raise HTTPException(
            status_code=503,
            detail=f"Sensor {sid.name} is not connected"
        )

    idx = sid.value
    corrected = sensor_manager.sensors[idx]
    offset = sensor_manager.offsets[idx]
    raw_value = corrected + offset
    relative_time = test_manager.get_relative_time()
    return Point(time=relative_time, value=raw_value)


@router.get("/{sensor_id}/zero", response_model=OffsetResponse, responses={
    400: {
        "description": "Invalid sensor_id provided.",
        "content": {
            "application/json": {
                "example": {"detail": f"Invalid sensor_id: INVALID. Valid values are: {VALID_SENSOR_VALUES}"}
            }
        }
    },
    503: {
        "description": "Sensor is not currently connected.",
        "content": {
            "application/json": {
                "example": {"detail": "Sensor FORCE is not connected"}
            }
        }
    }
})
async def get_sensor_zero_offset(sensor_id: str) -> OffsetResponse:
    """
    Get the current zero offset applied to raw readings for a sensor.
    The offset represents how much raw values are shifted to compute calibrated values.
    """
    try:
        sensor = SensorId[sensor_id.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sensor_id: {sensor_id}. Valid values are: {VALID_SENSOR_VALUES}"
        )

    # Check sensor connection status
    if not sensor_manager.is_sensor_connected(sensor):
        raise HTTPException(
            status_code=503,
            detail=f"Sensor {sensor_id.upper()} is not connected"
        )

    offset = sensor_manager.offsets[sensor.value]
    return OffsetResponse(offset=offset)


@router.put("/{sensor_id}/zero", status_code=204, responses={
    400: {
        "description": "Invalid sensor_id provided.",
        "content": {
            "application/json": {
                "example": {"detail": f"Invalid sensor_id: INVALID. Valid values are: {VALID_SENSOR_VALUES}"}
            }
        }
    },
    503: {
        "description": "Sensor is not currently connected.",
        "content": {
            "application/json": {
                "example": {"detail": "Sensor FORCE is not connected"}
            }
        }
    }
})
async def zero_sensor(sensor_id: str) -> None:
    """
    Zero a sensor by recording its current value.
    Future readings from this sensor will be adjusted by subtracting this value.
    """
    try:
        # Convert string to SensorId enum
        sensor = SensorId[sensor_id.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sensor_id: {sensor_id}. Valid values are: {', '.join([s.name for s in SensorId])}"
        )
    
    # Check sensor connection status
    if not sensor_manager.is_sensor_connected(sensor):
        raise HTTPException(
            status_code=503,
            detail=f"Sensor {sensor.name} is not connected"
        )
    
    # Send command to sensor manager via event hub
    event_hub.send_all_on_topic("sensor_command", {"action": "zero", "sensor_id": sensor})
