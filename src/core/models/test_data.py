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
    dim_length: float
    dim_height: float
    dim_width: float
    loading_mode: str
    sensor_spacing: float
    ext_support_spacing: float
    load_point_spacing: float