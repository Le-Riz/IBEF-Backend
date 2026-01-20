from pydantic.dataclasses import dataclass

@dataclass
class TestMetaData:
    """
    Data class representing metadata for a test.
    Compatible with both dataclass operations and Pydantic validation.
    """
    test_id: str
    date: str
    operator_name: str
    specimen_code: str
    dim_length: float = 0.0
    dim_height: float = 0.0
    dim_width: float = 0.0
    loading_mode: str = ""
    sensor_spacing: float = 0.0
    ext_sensor_spacing: float = 0.0
    ext_support_spacing: float = 0.0
    load_point_spacing: float = 0.0