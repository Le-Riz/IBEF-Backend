"""API Response Schemas.

This module defines Pydantic models for all API responses, including health checks,
data points, test status, and historical data structures.
"""

from typing import List, Any, Union
from core.models.sensor_enum import SensorId
from pydantic import BaseModel
from core.models.test_data import TestMetaData
from core.models.test_state import TestState


class HealthOK(BaseModel):
    """Basic health check response.
    
    Attributes:
        status: Health status as string (e.g., 'ok', 'healthy').
    """
    status: str


class AppHealthOK(BaseModel):
    """Application-level health check response.
    
    Attributes:
        status: Health status as string.
        app: Application name or version.
    """
    status: str
    app: str


class Point(BaseModel):
    """Single data point with timestamp.
    
    Attributes:
        time: Timestamp in seconds.
        value: Numeric value of the measurement.
    """
    time: float
    value: float

class OffsetResponse(BaseModel):
    """Sensor offset calibration response.
    
    Attributes:
        offset: Offset value for sensor calibration.
    """
    offset: float

class DictPoint(BaseModel):
    """Complete sensor data with raw, processed, and offset values.
    
    Attributes:
        raw: Dictionary of raw sensor measurements by sensor ID.
        data: Dictionary of processed sensor measurements by sensor ID.
        zeros: Dictionary of sensor offset calibrations by sensor ID.
    """
    raw: dict[str, Point]
    data: dict[str, Point]
    zeros: dict[str, OffsetResponse]

class PointsList(BaseModel):
    """List of data points.
    
    Attributes:
        list: Collection of Point objects.
    """
    list: List[Point]


class HistoryList(BaseModel):
    """List of historical data identifiers.
    
    Attributes:
        list: Collection of history file or record identifiers.
    """
    list: List[str]


class EmptyResponse(BaseModel):
    """Empty response model for endpoints with no return data."""
    pass


class FieldsResponse(BaseModel):
    """Response containing field metadata.
    
    Attributes:
        fields: Either a list of field definitions or TestMetaData object.
    """
    fields: Union[List[Any], TestMetaData]


class MessageResponse(BaseModel):
    """Generic message response.
    
    Attributes:
        message: Response message text.
    """
    message: str


class TestStatusResponse(BaseModel):
    """Test execution status response.
    
    Attributes:
        status: Current state of the test (e.g., running, completed, failed).
    """
    status: TestState
